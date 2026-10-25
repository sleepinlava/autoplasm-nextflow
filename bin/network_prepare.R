#!/usr/bin/env Rscript
# Prepare the compositional abundance matrix for FastSpar.
#
# Converts the merged plasmid abundance table into FastSpar's OTU-table
# layout (rows = contigs, columns = samples, first header cell ``#OTU ID``).
# Require measured integer raw counts (shared quantification uses CoverM count).
# Coverage is not a substitute for absolute read counts.
#
# FastSpar input best practices (phanta pipeline, bhattlab/phanta; scwatts/
# fastspar issue #1): prevalence-filter contigs before the SparCC run
# (--min-prevalence, phanta uses 0.2) and drop all-zero samples, which would
# otherwise give degenerate correlations.
#
# Missing is never zero: use integer measured raw_count only.
# Prevalence denominator is the initial nonzero cohort; then remove any
# newly empty samples and test final eligibility. No iterative refiltering.

suppressPackageStartupMessages(library(data.table))

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
  "min-prevalence" = list(default = "0.2"),
  out = list(required = TRUE),
  metadata = list(required = FALSE),
  "min-samples" = list(default = "2"),
  "out-status" = list(required = FALSE),
  "eligible-out" = list(required = FALSE)
)
opts <- parse_args(commandArgs(trailingOnly = TRUE), spec)
min_prev <- suppressWarnings(as.numeric(opts[["min-prevalence"]]))
if (is.na(min_prev) || min_prev < 0 || min_prev > 1) {
  die(paste0("argument --min-prevalence: invalid value: '", opts[["min-prevalence"]],
             "' (expected a number between 0 and 1)"))
}

min_samples <- suppressWarnings(as.numeric(opts[["min-samples"]]))
if (!is.finite(min_samples) || min_samples < 2 || min_samples != floor(min_samples))
  die("--min-samples must be an integer >=2")
if (!is.null(opts[["eligible-out"]]) && file.exists(opts[["eligible-out"]]))
  die("refusing preexisting eligible matrix; use a fresh output directory")

ab <- suppressWarnings(fread(opts$abundance, fill = TRUE, colClasses = "character",
                             na.strings = NULL))
if ("contig_id" %in% names(ab)) {
  cid <- as.character(ab$contig_id)
} else if ("plasmid_id" %in% names(ab)) {
  cid <- as.character(ab$plasmid_id)
} else {
  cid <- rep("", nrow(ab))
}
raw <- if ("raw_count" %in% names(ab)) as.character(ab$raw_count) else rep("", nrow(ab))
raw[is.na(raw) | raw == "NA"] <- ""
if (!"sample_id" %in% names(ab) || !any(c("contig_id", "plasmid_id") %in% names(ab)))
  die(paste0(opts$abundance, ": missing sample_id or feature ID column"))
if (!"raw_count" %in% names(ab))
  die(paste0(opts$abundance, ": missing raw_count column; coverage is not a count"))
value <- raw
num <- suppressWarnings(as.numeric(value))
bad <- which(!is.finite(num) | num < 0 | num != floor(num) | num > 2^53 - 1)
if (length(bad)) {
  i <- bad[1L]
  die(sprintf("Invalid numeric value in %s:%d sample=%s feature=%s field=raw_count value='%s'; expected finite nonnegative exactly representable integer raw count; coverage is not a count",
              opts$abundance, i + 1L, ab$sample_id[i], cid[i], value[i]))
}

if (!is.null(opts$metadata)) {
  meta <- fread(opts$metadata, colClasses=c(sample_id="character"), na.strings=NULL)
  identity <- statistics_input_contract(data.frame(sample_id=ab$sample_id, feature=cid), meta, "feature", opts$abundance)
  samples <- identity$samples
} else {
  samples <- sort(unique(ab$sample_id))
  if (length(samples)) statistics_input_contract(data.frame(sample_id=ab$sample_id, feature=cid),
      data.frame(sample_id=samples), "feature", opts$abundance)
}
mat_dt <- data.table(contig=cid, sample=as.character(ab$sample_id), value=num)
if (nrow(mat_dt)) {
  wide <- dcast(mat_dt, contig ~ sample, value.var="value")
  setorder(wide, contig)
} else {
  wide <- data.table(contig=character())
  for (sample in samples) wide[[sample]] <- numeric()
}
features_before <- nrow(wide)

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
# (raw count > 0) in >= ceil(min_prevalence * n_samples) samples.
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
# Prevalence filtering can create new empty sample columns. Remove them once;
# preserve the already-applied prevalence denominator and threshold.
post_empty <- kept_samples[vapply(kept_samples, function(sample) sum(wide[[sample]]) == 0, logical(1))]
kept_samples <- setdiff(kept_samples, post_empty)
cat(sprintf("filtered %d low-prevalence contig(s), dropped %d initially empty and %d newly empty sample(s)\n",
            n_filtered, length(empty_samples), length(post_empty)), file=stderr())

out <- data.table("#OTU ID" = wide$contig)
for (s in kept_samples) {
  v <- if (s %in% names(wide)) wide[[s]] else rep(0L, nrow(wide))
  out[[s]] <- sprintf("%.0f", v)
}
fwrite(out, opts$out, sep = "\t", quote = FALSE, na = "")
cat(sprintf("fastspar input: %d contig(s) x %d sample(s)\n",
            nrow(out), length(kept_samples)))

# FastSpar1.0.0 requires >=4 components (src/fastspar.cpp:127-131).
# Producing a preparation/status file is distinct from running the estimator.
reason <- if (nrow(out) < 4) "insufficient_features" else if (length(kept_samples) < min_samples) "insufficient_samples" else "eligible"
status <- list(eligible=identical(reason,"eligible"), reason=reason,
  min_features=4L, min_samples=min_samples,
  features_before=features_before, features_after=nrow(out),
  prevalence=min_prev, prevalence_denominator=length(samples)-length(empty_samples),
  observed_or_expected_sample_ids=as.list(samples), included_sample_ids=as.list(kept_samples),
  excluded_initial_zero=as.list(empty_samples), excluded_zero_after_prevalence=as.list(post_empty),
  metadata_status=if (is.null(opts$metadata)) "not_provided" else "provided",
  count_unit="primary_read_alignment", policy="single prevalence filter, then remove empty columns; no iterative filtering")
if (!is.null(opts[["out-status"]])) jsonlite::write_json(status,opts[["out-status"]],auto_unbox=TRUE,pretty=TRUE)
if (!is.null(opts[["eligible-out"]]) && status$eligible) {
  if (!file.copy(opts$out,opts[["eligible-out"]])) die("cannot write eligible matrix")
}
cat(sprintf("network eligibility: %s; %d feature(s), %d sample(s)\n",reason,nrow(out),length(kept_samples)),file=stderr())
