#!/usr/bin/env Rscript
# Prepare the compositional abundance matrix for FastSpar.
#
# Converts the merged plasmid abundance table into FastSpar's OTU-table
# layout (rows = contigs, columns = samples, first header cell ``#OTU ID``).
# CoverM does not emit raw counts, so rounded coverage is used as the count
# proxy (same convention as the ABI DESeq2 script); a stderr warning notes
# this because FastSpar expects integer absolute counts.
#
# FastSpar input best practices (phanta pipeline, bhattlab/phanta; scwatts/
# fastspar issue #1): prevalence-filter contigs before the SparCC run
# (--min-prevalence, phanta uses 0.2) and drop all-zero samples, which would
# otherwise give degenerate correlations.
#
# R equivalent of bin/network_prepare.py: the id column is contig_id or
# plasmid_id; the value is raw_count when non-empty, else coverage, else
# "0"; values are max(0, round(as.numeric(x))) with non-numeric -> 0.

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

spec <- list(
  abundance = list(required = TRUE),
  "min-prevalence" = list(default = "0.2"),
  out = list(required = TRUE)
)
opts <- parse_args(commandArgs(trailingOnly = TRUE), spec)
min_prev <- suppressWarnings(as.numeric(opts[["min-prevalence"]]))
if (is.na(min_prev) || min_prev < 0 || min_prev > 1) {
  die(paste0("argument --min-prevalence: invalid value: '", opts[["min-prevalence"]],
             "' (expected a number between 0 and 1)"))
}

ab <- suppressWarnings(fread(opts$abundance, fill = TRUE))
if ("contig_id" %in% names(ab)) {
  cid <- as.character(ab$contig_id)
} else if ("plasmid_id" %in% names(ab)) {
  cid <- as.character(ab$plasmid_id)
} else {
  cid <- rep("", nrow(ab))
}
raw <- if ("raw_count" %in% names(ab)) as.character(ab$raw_count) else rep("", nrow(ab))
cov <- if ("coverage" %in% names(ab)) as.character(ab$coverage) else rep("", nrow(ab))
raw[is.na(raw)] <- ""
cov[is.na(cov)] <- ""
if (any(!nzchar(raw) & nzchar(cov))) {
  cat("warning: rounding coverage to counts; FastSpar expects integer counts\n",
      file = stderr())
}
value <- ifelse(nzchar(raw), raw, ifelse(nzchar(cov), cov, "0"))
num <- suppressWarnings(as.numeric(value))
num[is.na(num)] <- 0
num[num < 0] <- 0
num <- round(num)

mat_dt <- data.table(contig = cid, sample = as.character(ab$sample_id),
                     value = num)
mat_dt[is.na(sample), sample := ""]
wide <- dcast(mat_dt, contig ~ sample, value.var = "value",
              fun.aggregate = function(x) x[length(x)], fill = 0)
setorder(wide, contig)

samples <- sort(unique(mat_dt$sample))
contigs <- sort(unique(mat_dt$contig))

# FastSpar degenerates on all-zero samples (fastspar issue #1): drop them.
empty_samples <- character(0)
for (s in samples) {
  v <- if (s %in% names(wide)) wide[[s]] else rep(0, nrow(wide))
  if (all(v == 0)) empty_samples <- c(empty_samples, s)
}
kept_samples <- setdiff(samples, empty_samples)
if (length(empty_samples) > 0) {
  cat(sprintf("note: dropped %d empty sample(s): %s\n",
              length(empty_samples), paste(empty_samples, collapse = ", ")),
      file = stderr())
}

# Prevalence filter (phanta convention): keep contigs detected
# (rounded value > 0) in >= ceil(min_prevalence * n_samples) samples.
n_filtered <- 0L
if (nrow(wide) > 0 && min_prev > 0 && length(kept_samples) > 0) {
  detected <- vapply(kept_samples, function(s) {
    v <- if (s %in% names(wide)) wide[[s]] else rep(0, nrow(wide))
    v > 0
  }, logical(nrow(wide)))
  if (is.null(dim(detected))) detected <- matrix(detected, ncol = length(kept_samples))
  n_det <- rowSums(detected)
  keep_rows <- n_det >= ceiling(min_prev * length(kept_samples))
  n_filtered <- sum(!keep_rows)
  wide <- wide[keep_rows, ]
} else if (nrow(wide) > 0 && min_prev > 0) {
  # no samples left at all: every contig fails the prevalence filter
  n_filtered <- nrow(wide)
  wide <- wide[0, ]
}
cat(sprintf("filtered %d low-prevalence contig(s), %d empty sample(s)\n",
            n_filtered, length(empty_samples)), file = stderr())

out <- data.table("#OTU ID" = wide$contig)
for (s in kept_samples) {
  v <- if (s %in% names(wide)) wide[[s]] else rep(0L, nrow(wide))
  out[[s]] <- as.integer(v)
}
fwrite(out, opts$out, sep = "\t", quote = FALSE, na = "")
cat(sprintf("fastspar input: %d contig(s) x %d sample(s)\n",
            nrow(out), length(kept_samples)))
