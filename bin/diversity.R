#!/usr/bin/env Rscript
# Alpha/beta diversity analysis over the merged contig abundance table.
#
# Alpha: richness (contigs with coverage > 0) via vegan::specnumber, the
# Shannon index (natural log, as in the Python reference) via
# vegan::diversity(index = "shannon"), the Gini-Simpson index via
# vegan::diversity(index = "simpson") (1 - sum(p^2)), and Pielou evenness
# H/log(S) (guarded to 0.000000 when S <= 1 or H == 0). These are the same
# vegan calls that phyloseq::estimate_richness wraps. Beta: pairwise
# Bray-Curtis dissimilarity via vegan::vegdist(method = "bray").
#
# --beta-normalization tss scales each sample's coverages to proportions
# (total-sum scaling) before vegdist, the MetaPhlAn calculate_diversity.R
# convention; TSS is the recommended practice for relative-abundance-like
# data. The default "none" preserves the historical raw-coverage behavior.
#
# vegdist returns NaN for sample pairs whose combined coverage is all-zero
# (0/0); the Python implementation emitted 0.0 in that case, so NaN values
# are converted to 0 here to keep the output schema compatible, and a stderr
# warning lists how many sample pairs were coerced. Per the vegan
# documentation, empty samples should ideally be removed from the analysis
# rather than coerced; the coercion is kept for output schema compatibility.
# A single sample yields a 1x1 beta matrix of 0.000000 instead of an error.
#
# Output schemas follow the ``sample_diversity`` standard table.

suppressPackageStartupMessages({
  library(vegan)
  library(data.table)
})

# Load the shared identity contract alongside the executable, including PATH invocation.
script_file <- sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value=TRUE)[1L])
source(file.path(dirname(normalizePath(script_file)), "statistics_input_contract.R"))

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

spec <- list(
  abundance = list(required = TRUE),
  metadata = list(required = TRUE),
  "out-metrics" = list(required = TRUE),
  "out-beta" = list(required = TRUE),
  "beta-normalization" = list(default = "none"),
  "out-status" = list(required = FALSE)
)
opts <- parse_args(commandArgs(trailingOnly = TRUE), spec)
beta_norm <- opts[["beta-normalization"]]
if (!(beta_norm %in% c("none", "tss"))) {
  die(paste0("argument --beta-normalization: invalid choice: '", beta_norm,
             "' (choose from 'none', 'tss')"))
}

ab <- fread(opts$abundance, colClasses = c(sample_id = "character", contig_id = "character"),
            na.strings = NULL)
required <- c("sample_id", "contig_id", "coverage")
if (!all(required %in% names(ab)))
  die(paste0(opts$abundance, ": missing required columns: ", paste(setdiff(required, names(ab)), collapse = ", ")))
cov <- suppressWarnings(as.numeric(ab$coverage))
bad <- which(!is.finite(cov) | cov < 0)
if (length(bad)) {
  i <- bad[1L]
  die(sprintf("Invalid numeric value in %s:%d sample=%s feature=%s field=coverage value='%s'; expected finite nonnegative measurement",
              opts$abundance, i + 1L, ab$sample_id[i], ab$contig_id[i], ab$coverage[i]))
}
ab[, coverage := cov]

meta <- read.delim(opts$metadata, colClasses = c(sample_id = "character", group = "character"),
                   check.names = FALSE, stringsAsFactors = FALSE, na.strings = NULL)
# Preserve the existing missing-group policy without decoding identifier tokens.
if ("group" %in% names(meta)) meta$group[!is.na(meta$group) & meta$group == "NA"] <- NA
identity <- statistics_input_contract(ab, meta, "contig_id", opts$abundance)
groups <- if ("group" %in% names(meta)) stats::setNames(meta$group, meta$sample_id) else character(0)
samples <- identity$samples
contigs <- identity$features
if (length(contigs)) {
  wide <- dcast(ab, contig_id ~ sample_id, value.var = "coverage")
  setorder(wide, contig_id)
  mat <- as.matrix(wide[, -1, with = FALSE])
  rownames(mat) <- wide$contig_id
  mat <- mat[contigs, samples, drop = FALSE]
} else {
  mat <- matrix(0, nrow=0L, ncol=length(samples), dimnames=list(character(), samples))
}

site_mat <- t(mat)
# Explicit sample names are essential: vegan may simplify a one-column matrix
# to an unnamed scalar/vector. Empty samples have alpha0 by existing policy.
rich <- stats::setNames(rowSums(site_mat > 0), samples)
sh <- simp <- stats::setNames(numeric(length(samples)), samples)
nonempty <- rowSums(site_mat) > 0
if (any(nonempty)) {
  # One-column matrices are treated as one vector by vegan, pooling samples.
  # Evaluate each community row explicitly, including the one-feature case.
  sh[nonempty] <- vapply(which(nonempty), function(i)
    diversity(as.numeric(site_mat[i, ]), index="shannon"), numeric(1))
  simp[nonempty] <- vapply(which(nonempty), function(i)
    diversity(as.numeric(site_mat[i, ]), index="simpson"), numeric(1))
}
pielou <- vapply(seq_along(samples), function(i) {
  s_i <- rich[i]
  h_i <- sh[i]
  if (is.na(s_i) || s_i <= 1 || is.na(h_i) || h_i == 0) return(0.0)
  h_i / log(s_i)
}, numeric(1))
names(pielou) <- samples

metrics <- rbindlist(lapply(samples, function(s) data.table(
  sample_id = s,
  metric = c("richness", "shannon", "simpson", "pielou"),
  value = c(sprintf("%d", as.integer(rich[s])), sprintf("%.6f", sh[s]),
            sprintf("%.6f", simp[s]), sprintf("%.6f", pielou[s])),
  group = unname(if (s %in% names(groups)) groups[s] else "")
)))
metrics[is.na(group), group := ""]

fwrite(metrics, opts[["out-metrics"]], sep = "\t", quote = "auto", na = "")

beta_mat <- site_mat
if (beta_norm == "tss") {
  rs <- rowSums(beta_mat)
  beta_mat <- beta_mat / ifelse(rs > 0, rs, 1)
}
if (ncol(beta_mat) == 0) {
  bd <- matrix(0, nrow=length(samples), ncol=length(samples), dimnames=list(samples, samples))
} else if (nrow(beta_mat) >= 2) {
  bd <- suppressWarnings(as.matrix(vegdist(beta_mat, method = "bray")))
  n_coerced <- sum(is.nan(bd[upper.tri(bd)]))
  if (n_coerced > 0) {
    cat(sprintf("warning: %d sample pair(s) with all-zero combined coverage; NaN Bray-Curtis coerced to 0.000000\n",
                n_coerced), file = stderr())
  }
  bd[is.nan(bd)] <- 0
} else {
  bd <- matrix(0, nrow = 1L, ncol = 1L,
               dimnames = list(rownames(beta_mat), rownames(beta_mat)))
}
beta <- data.frame(sample_id = rownames(bd), bd, check.names = FALSE,
                   stringsAsFactors = FALSE)
for (j in seq_len(ncol(bd))) beta[[j + 1]] <- sprintf("%.6f", bd[, j])
write.table(beta, file = opts[["out-beta"]], sep = "\t", quote = FALSE,
            row.names = FALSE, col.names = c("sample_id", colnames(bd)))

if (!is.null(opts[["out-status"]])) {
  jsonlite::write_json(list(status=if (!length(contigs)) "zero_feature_input" else if (all(rowSums(site_mat)==0)) "measured_all_zero" else "measured",
    sample_ids=as.list(samples), feature_count=length(contigs), zero_samples=as.list(samples[rowSums(site_mat)==0]),
    alpha_empty_policy="richness/shannon/simpson/pielou0", beta_zero_pair_policy="Bray-Curtis undefined for two zeros; compatibility convention0, not measured similarity",
    beta_normalization=beta_norm), opts[["out-status"]], auto_unbox=TRUE, pretty=TRUE)
}
