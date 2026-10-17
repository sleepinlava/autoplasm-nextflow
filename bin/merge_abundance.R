#!/usr/bin/env Rscript
# Merge per-sample CoverM tables into a long-format abundance table.
#
# Production workflows pass ``--sample-ids`` alongside the corresponding
# table paths. Filename inference remains for older standalone CLI callers,
# but it is ambiguous for IDs containing dots or suffix-like text.
#
# R equivalent of bin/merge_abundance.py: value columns (RPKM/TPM/coverage)
# are copied verbatim as strings (all columns are read as character), and
# error messages / exit codes match the Python implementation.

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

sample_from_name <- function(path) {
  name <- basename(path)
  if (grepl("__", name, fixed = TRUE)) return(sub("__.*$", "", name))
  for (suffix in c(".short.coverm.tsv", ".long.coverm.tsv",
                   ".contig_coverm.tsv", ".coverm.tsv")) {
    if (endsWith(name, suffix))
      return(substring(name, 1, nchar(name) - nchar(suffix)))
  }
  sub("\\.[^.]*$", "", name)
}

read_table <- function(path, sample, seen_features) {
  if (!file.exists(path))
    die(paste0("Cannot read CoverM table ", path, ": no such file or directory"))
  dt <- tryCatch(
    fread(path, sep = "\t", colClasses = "character"),
    error = function(e) e
  )
  if (inherits(dt, "error")) {
    if (grepl("[Ee]mpty", conditionMessage(dt)))
      die(paste0(path, ": missing TSV header"))
    die(paste0("Cannot read CoverM table ", path, ": ", conditionMessage(dt)))
  }
  if (ncol(dt) == 0)
    die(paste0(path, ": missing TSV header"))
  names(dt) <- trimws(names(dt))
  fields <- names(dt)
  id_col <- fields[1]
  mean_col <- Find(function(f) endsWith(tolower(f), "mean"), fields)
  tpm_col <- Find(function(f) endsWith(tolower(f), "tpm"), fields)
  rpkm_col <- Find(function(f) endsWith(tolower(f), "rpkm"), fields)
  if (nrow(dt) == 0)
    return(list(rows = data.table(), seen = seen_features))
  rows <- list()
  for (k in seq_len(nrow(dt))) {
    feature <- trimws(dt[[id_col]][k])
    if (!nzchar(feature)) next
    key <- paste(sample, feature, sep = "\t")
    line_number <- k + 1
    if (key %in% names(seen_features))
      die(sprintf("Duplicate ('%s', '%s') feature in %s:%d; first seen in %s",
                  sample, feature, path, line_number, seen_features[[key]]))
    seen_features[[key]] <- paste0(path, ":", line_number)
    get_col <- function(col) {
      if (is.null(col)) return("")
      v <- dt[[col]][k]
      if (is.na(v)) "" else v
    }
    rows[[length(rows) + 1]] <- data.table(
      feature = feature,
      sample_id = sample,
      rpkm = get_col(rpkm_col),
      tpm = get_col(tpm_col),
      coverage = get_col(mean_col),
      raw_count = "",
      mapper = "")
  }
  list(rows = if (length(rows)) rbindlist(rows) else data.table(), seen = seen_features)
}

spec <- list(
  tables = list(required = TRUE, multi = TRUE),
  "sample-ids" = list(default = NULL, multi = TRUE),
  out = list(required = TRUE),
  mapper = list(default = ""),
  "id-column" = list(default = "contig_id")
)
opts <- parse_args(commandArgs(trailingOnly = TRUE), spec)
tables <- opts$tables
sample_ids <- opts[["sample-ids"]]
mapper <- opts$mapper
id_column <- opts[["id-column"]]
out_path <- opts$out

if (!is.null(sample_ids)) {
  if (length(sample_ids) != length(tables))
    die(sprintf("--sample-ids has %d value(s) for %d table(s)",
                length(sample_ids), length(tables)))
  if (any(!nzchar(trimws(sample_ids))))
    die("sample IDs must not be empty")
  if (anyDuplicated(sample_ids))
    die("duplicate sample IDs in --sample-ids")
} else {
  sample_ids <- vapply(tables, sample_from_name, character(1))
  if (anyDuplicated(sample_ids))
    die("filename inference produced duplicate sample IDs; pass --sample-ids explicitly")
}

all_rows <- list()
seen_features <- character(0)
for (k in seq_along(tables)) {
  res <- read_table(tables[k], sample_ids[k], seen_features)
  seen_features <- res$seen
  if (nrow(res$rows)) all_rows[[length(all_rows) + 1]] <- res$rows
}
merged <- if (length(all_rows)) rbindlist(all_rows) else data.table()
mapper_value <- mapper
if (nrow(merged)) {
  merged[, mapper := mapper_value]
  setnames(merged, "feature", id_column)
} else {
  merged <- data.table(feature = character(0), sample_id = character(0),
                       rpkm = character(0), tpm = character(0),
                       coverage = character(0), raw_count = character(0),
                       mapper = character(0))
  merged[, mapper := mapper_value]
  setnames(merged, "feature", id_column)
}
setcolorder(merged, c(id_column, "sample_id", "rpkm", "tpm", "coverage",
                      "raw_count", "mapper"))

out_dir <- dirname(out_path)
if (!dir.exists(out_dir)) dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
tmp <- tempfile(pattern = paste0(".", basename(out_path), "."),
                tmpdir = out_dir, fileext = ".tmp")
ok <- tryCatch({
  fwrite(merged, tmp, sep = "\t", quote = FALSE, na = "")
  TRUE
}, error = function(e) FALSE)
if (!ok || !file.rename(tmp, out_path)) {
  unlink(tmp)
  die(paste0("cannot write output table ", out_path))
}
cat(sprintf("merged %d table(s) -> %d rows\n", length(tables), nrow(merged)),
    file = stderr())
