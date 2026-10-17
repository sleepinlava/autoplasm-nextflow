#!/usr/bin/env Rscript
# Internal effect-size differential plasmid abundance between groups.
#
# Standalone implementation of the ABI ``internal_effect_size`` method for
# the ``multisample_differential_abundance`` node. For every pair of groups
# with at least ``--min-replicates`` samples it computes, per contig:
#
# * log2 fold change of mean coverage (pseudocount 1e-6),
# * Welch's t-test p-value (two-sided),
# * Benjamini-Hochberg adjusted p-values,
# * Hedges' g effect size.
#
# Difference vs. the Python reference implementation: the p-value is computed
# with stats::t.test (Welch two-sided, t distribution) instead of the normal
# (erfc) approximation of the Welch statistic; this is the intended upgrade to
# established R statistics. As before, when the Welch standard error is zero
# (zero variance on both sides) or the test is otherwise not computable
# (e.g. < 2 observations per group), the p-value falls back to 1.0. Hedges' g
# is computed in base R with the identical formula (pooled SD plus the
# 1 - 3/(4*(na+nb)-9) small-sample correction). BH adjustment uses
# stats::p.adjust(method = "BH") over all tests actually performed.
#
# Prevalence filtering follows the Maaslin2 (min_prevalence = 0.10) and
# ANCOM-BC2 (prv_cut = 0.10) convention: per group pair, contigs are tested
# only when detected (coverage > 0) in at least
# ceil(--min-prevalence * n_compared_samples) of the compared samples, so
# all-zero/single-detection contigs do not dilute the BH denominator.
# Per-pair filtered counts are logged to stderr.
#
# Output schema follows the ABI ``differential_abundance`` standard table.

suppressPackageStartupMessages(library(data.table))

die <- function(msg) {
  cat(msg, "\n", file = stderr(), sep = "")
  quit(save = "no", status = 2)
}

parse_args <- function(argv, spec) {
  opts <- lapply(spec, function(s) if (is.null(s$default)) NULL else s$default)
  given <- character(0)
  i <- 1
  while (i <= length(argv)) {
    tok <- argv[i]
    if (!startsWith(tok, "--")) die(paste0("unrecognized argument: ", tok))
    flag <- substring(tok, 3)
    value <- NULL
    eq <- regexpr("=", flag, fixed = TRUE)
    if (eq > 0) {
      value <- substring(flag, eq + 1)
      flag <- substring(flag, 1, eq - 1)
    }
    if (!flag %in% names(spec)) die(paste0("unrecognized argument: --", flag))
    if (isTRUE(spec[[flag]]$multi)) {
      vals <- character(0)
      if (!is.null(value)) {
        vals <- value
      } else {
        j <- i + 1
        while (j <= length(argv) && !startsWith(argv[j], "--")) {
          vals <- c(vals, argv[j])
          j <- j + 1
        }
        i <- j - 1
      }
      opts[[flag]] <- vals
    } else {
      if (!is.null(value)) {
        opts[[flag]] <- value
      } else {
        if (i + 1 > length(argv) || startsWith(argv[i + 1], "--"))
          die(paste0("argument --", flag, ": expected one argument"))
        opts[[flag]] <- argv[i + 1]
        i <- i + 1
      }
    }
    given <- c(given, flag)
    i <- i + 1
  }
  missing <- names(spec)[vapply(names(spec), function(nm)
    isTRUE(spec[[nm]]$required) && !(nm %in% given), logical(1))]
  if (length(missing))
    die(paste0("the following arguments are required: ",
               paste0("--", missing, collapse = ", ")))
  opts
}

PSEUDOCOUNT <- 1e-6

welch_p <- function(a, b) {
  res <- tryCatch(stats::t.test(a, b), error = function(e) NULL)
  if (is.null(res)) return(1.0)
  res$p.value
}

hedges_g <- function(a, b) {
  na <- length(a)
  nb <- length(b)
  ma <- sum(a) / na
  mb <- sum(b) / nb
  va <- if (na > 1) sum((a - ma)^2) / (na - 1) else 0.0
  vb <- if (nb > 1) sum((b - mb)^2) / (nb - 1) else 0.0
  pooled <- if (na + nb > 2) sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2)) else 0.0
  if (pooled == 0) return(0.0)
  d <- (ma - mb) / pooled
  correction <- if (na + nb > 2) 1 - 3 / (4 * (na + nb) - 9) else 1.0
  d * correction
}

spec <- list(
  abundance = list(required = TRUE),
  metadata = list(required = TRUE),
  "min-replicates" = list(default = "3"),
  "min-prevalence" = list(default = "0.1"),
  out = list(required = TRUE)
)
opts <- parse_args(commandArgs(trailingOnly = TRUE), spec)
min_rep <- as.integer(opts[["min-replicates"]])
min_prev <- suppressWarnings(as.numeric(opts[["min-prevalence"]]))
if (is.na(min_prev) || min_prev < 0 || min_prev > 1) {
  die(paste0("argument --min-prevalence: invalid value: '", opts[["min-prevalence"]],
             "' (expected a number between 0 and 1)"))
}

ab <- fread(opts$abundance)
cov <- suppressWarnings(as.numeric(ab$coverage))
cov[is.na(cov)] <- 0
ab[, coverage := cov]

by_sample <- split(ab, ab$sample_id)

meta <- fread(opts$metadata)
grp_samples <- list()
if (nrow(meta) > 0) {
  sid <- as.character(meta$sample_id)
  grp <- as.character(meta$group)
  ok <- nzchar(sid) & nzchar(grp)
  for (i in which(ok)) grp_samples[[grp[i]]] <- c(grp_samples[[grp[i]]], sid[i])
}
eligible <- grp_samples[vapply(grp_samples, function(s)
  length(s[s %in% names(by_sample)]) >= min_rep, logical(1))]

contigs <- sort(unique(ab$contig_id))
egroups <- sort(names(eligible))

rows <- list()
pvals <- numeric(0)
if (length(egroups) >= 2) {
  for (i in seq_len(length(egroups) - 1)) {
    for (j in (i + 1):length(egroups)) {
      g1 <- egroups[i]
      g2 <- egroups[j]
      s1 <- eligible[[g1]][eligible[[g1]] %in% names(by_sample)]
      s2 <- eligible[[g2]][eligible[[g2]] %in% names(by_sample)]
      compared <- c(s1, s2)
      keep <- rep(TRUE, length(contigs))
      if (min_prev > 0) {
        detected <- integer(length(contigs))
        for (s in compared) {
          dt_s <- by_sample[[s]]
          det_names <- dt_s$contig_id[dt_s$coverage > 0]
          detected <- detected + (contigs %in% det_names)
        }
        keep <- detected >= ceiling(min_prev * length(compared))
        cat(sprintf("%s vs %s: filtered %d/%d contig(s) below min-prevalence %g\n",
                    g1, g2, sum(!keep), length(contigs), min_prev), file = stderr())
      }
      for (cid in contigs[keep]) {
        a <- vapply(s1, function(s) by_sample[[s]][by_sample[[s]]$contig_id == cid, coverage][1],
                    numeric(1))
        b <- vapply(s2, function(s) by_sample[[s]][by_sample[[s]]$contig_id == cid, coverage][1],
                    numeric(1))
        a[is.na(a)] <- 0
        b[is.na(b)] <- 0
        ma <- sum(a) / length(a)
        mb <- sum(b) / length(b)
        log2fc <- log2((ma + PSEUDOCOUNT) / (mb + PSEUDOCOUNT))
        p <- welch_p(a, b)
        g <- hedges_g(a, b)
        rows[[length(rows) + 1]] <- data.table(
          contig_id = cid, group1 = g1, group2 = g2,
          log2fc = sprintf("%.6f", log2fc),
          pvalue = sprintf("%.6g", p),
          effect_size = sprintf("%.6f", g),
          method = "internal_effect_size")
        pvals <- c(pvals, p)
      }
    }
  }
}

padj <- if (length(pvals)) p.adjust(pvals, method = "BH") else numeric(0)
if (length(rows)) {
  out <- rbindlist(rows)
  out$padj <- if (length(padj)) sprintf("%.6g", padj) else character(nrow(out))
} else {
  out <- data.table(contig_id = character(0), group1 = character(0),
                    group2 = character(0), log2fc = character(0),
                    pvalue = character(0), padj = character(0),
                    effect_size = character(0), method = character(0))
}
setcolorder(out, c("contig_id", "group1", "group2", "log2fc", "pvalue",
                   "padj", "effect_size", "method"))
fwrite(out, opts$out, sep = "\t", quote = FALSE, na = "")
cat(sprintf("differential abundance: %d test(s), %d eligible group(s)\n",
            nrow(out), length(eligible)))
