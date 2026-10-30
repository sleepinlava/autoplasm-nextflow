#!/usr/bin/env Rscript
# Prepare a sample-aware FASTA input for cross-sample plasmid clustering.
#
# R port of bin/plasmid_catalog_prepare.py. Accepted input basenames are
# ``<sample>.plasmid_contigs.fasta``, the legacy ``<sample>__plasmid_contigs.fasta``,
# and ``plasmid_contigs.fasta`` inside a sample-named directory. Every output
# identifier is ``sample|contig``.
#
# Input FASTAs are validated line by line (base R) so malformed-header errors
# carry the same ``path:line`` context as the Python original; the validated
# catalog is written with Biostrings::writeXStringSet (80-column wrapping) and
# installed via atomic rename.
#
# Optional length prefilter (``--min-length``, 0 = off): published plasmidome
# catalogs prefilter short contigs before MMseqs2 clustering (e.g. the Debroas
# lab global metaplasmidome, Microbiome 2025, 2 kb cutoff). Skipped sequences
# are counted and reported in the stdout summary.

suppressPackageStartupMessages(library(Biostrings))

die <- function(msg) {
  cat(msg, "\n", file = stderr(), sep = "")
  quit(save = "no", status = 2L, runLast = FALSE)
}

parse_cli <- function(argv, spec) {
  opts <- lapply(spec, function(s) s$default)
  names(opts) <- names(spec)
  i <- 1L
  n <- length(argv)
  while (i <= n) {
    tok <- argv[i]
    if (!startsWith(tok, "--")) die(paste0("unrecognized argument: '", tok, "'"))
    body <- substr(tok, 3L, nchar(tok))
    eq <- regexpr("=", body, fixed = TRUE)
    if (eq > 0L) {
      flag <- substr(body, 1L, eq - 1L)
      inline <- substr(body, eq + 1L, nchar(body))
      has_inline <- TRUE
    } else {
      flag <- body
      inline <- ""
      has_inline <- FALSE
    }
    dest <- gsub("-", "_", flag, fixed = TRUE)
    if (!dest %in% names(spec)) die(paste0("unrecognized arguments: --", flag))
    entry <- spec[[dest]]
    if (entry$mode == "multi") {
      vals <- if (has_inline) inline else character(0)
      j <- i + 1L
      while (j <= n && !startsWith(argv[j], "--")) {
        vals <- c(vals, argv[j])
        j <- j + 1L
      }
      i <- j - 1L
      if (length(vals) == 0L) die(paste0("argument --", flag, ": expected at least one argument"))
      if (isTRUE(entry$append)) opts[[dest]] <- c(opts[[dest]], vals) else opts[[dest]] <- vals
    } else {
      if (has_inline) {
        v <- inline
      } else {
        if (i + 1L > n || startsWith(argv[i + 1L], "--")) die(paste0("argument --", flag, ": expected one argument"))
        v <- argv[i + 1L]
        i <- i + 1L
      }
      opts[[dest]] <- v
    }
    i <- i + 1L
  }
  missing <- character(0)
  for (nm in names(spec)) {
    if (isTRUE(spec[[nm]]$required)) {
      val <- opts[[nm]]
      if (is.null(val) || length(val) == 0L || (is.character(val) && !all(nzchar(val)))) {
        missing <- c(missing, paste0("--", gsub("_", "-", nm, fixed = TRUE)))
      }
    }
  }
  if (length(missing) > 0L) die(paste0("the following arguments are required: ", paste(missing, collapse = ", ")))
  opts
}

infer_sample_id <- function(path) {
  name <- basename(path)
  suffix_modern <- ".plasmid_contigs.fasta"
  suffix_legacy <- "__plasmid_contigs.fasta"
  if (endsWith(name, suffix_modern)) {
    sample <- sub(paste0(suffix_modern, "$"), "", name)
  } else if (endsWith(name, suffix_legacy)) {
    sample <- sub(paste0(suffix_legacy, "$"), "", name)
  } else if (name == "plasmid_contigs.fasta") {
    dir_name <- dirname(path)
    sample <- if (dir_name %in% c(".", "")) "" else basename(dir_name)
  } else {
    die(paste0("Unsupported plasmid FASTA naming: ", path))
  }
  if (!nzchar(sample)) die(paste0("Invalid sample ID in ", path, ": sample ID is empty"))
  if (grepl("[[:space:]]", sample)) die(paste0("Invalid sample ID in ", path, ": whitespace is not allowed"))
  if (grepl("|", sample, fixed = TRUE)) die(paste0("Invalid sample ID in ", path, ": '|' is not allowed"))
  sample
}

first_token <- function(header) {
  sub("[[:space:]].*$", "", trimws(header))
}

read_fasta_records <- function(path) {
  if (!file.exists(path)) die(paste0("Cannot read FASTA ", path, ": No such file or directory"))
  lines <- readLines(path, warn = FALSE)
  lines <- sub("[\r\n]+$", "", lines)
  records <- list()
  name <- NULL
  seq <- character(0)
  flush <- function() {
    if (!is.null(name)) {
      records[[length(records) + 1L]] <<- list(id = name, seq = paste(seq, collapse = ""))
    }
  }
  for (ln in seq_along(lines)) {
    line <- lines[ln]
    if (startsWith(line, ">")) {
      flush()
      header <- trimws(substring(line, 2L))
      if (!nzchar(header)) die(paste0(path, ":", ln, ": empty FASTA header"))
      name <- first_token(header)
      seq <- character(0)
    } else if (nzchar(trimws(line))) {
      if (is.null(name)) die(paste0(path, ":", ln, ": sequence data before FASTA header"))
      seq <- c(seq, trimws(line))
    }
  }
  flush()
  records
}

main <- function() {
  spec <- list(
    contigs = list(mode = "multi", required = TRUE, default = NULL),
    out = list(mode = "single", required = TRUE, default = NULL),
    out_samples = list(mode = "single", default = NULL),
    min_length = list(mode = "single", default = "0")
  )
  args <- parse_cli(commandArgs(trailingOnly = TRUE), spec)
  min_length <- suppressWarnings(as.integer(args$min_length))
  if (is.na(min_length) || min_length < 0) {
    die(paste0("argument --min-length: invalid non-negative integer value: '", args$min_length, "'"))
  }

  paths <- sort(as.character(args$contigs), method = "radix")
  seen <- new.env(hash = TRUE, parent = emptyenv())
  records <- list()
  samples <- character(0)
  skipped <- 0L
  for (path in paths) {
    sample <- infer_sample_id(path)
    samples <- c(samples, sample)
    for (rec in read_fasta_records(path)) {
      if (min_length > 0L && nchar(rec$seq) < min_length) {
        skipped <- skipped + 1L
        next
      }
      header <- paste0(sample, "|", rec$id)
      if (exists(header, envir = seen, inherits = FALSE)) {
        die(sprintf("Duplicate FASTA identifier '%s' in %s; first seen in %s",
                    header, path, get(header, envir = seen)))
      }
      assign(header, path, envir = seen)
      records[[length(records) + 1L]] <- list(header = header, seq = rec$seq)
    }
  }

  out <- args$out
  if (!is.null(args$out_samples) &&
      normalizePath(args$out_samples, mustWork = FALSE) == normalizePath(out, mustWork = FALSE))
    die("Catalog and sample manifest must have distinct output paths")
  out_dir <- dirname(out)
  dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
  tmp <- tempfile(pattern = paste0(".", basename(out), "."), tmpdir = out_dir,
                  fileext = ".tmp")
  tryCatch({
    seqs <- BStringSet(vapply(records, function(r) r$seq, character(1)))
    names(seqs) <- vapply(records, function(r) r$header, character(1))
    writeXStringSet(seqs, tmp, width = 80L)
    if (!is.null(args$out_samples)) {
      dir.create(dirname(args$out_samples), recursive = TRUE, showWarnings = FALSE)
      samples_tmp <- tempfile(pattern = ".catalog_samples.", tmpdir = dirname(args$out_samples))
      on.exit(unlink(samples_tmp), add = TRUE)
      writeLines(c("sample_id", unique(samples)), samples_tmp, useBytes = TRUE)
      if (!file.rename(samples_tmp, args$out_samples)) die(paste0("Cannot write samples ", args$out_samples))
    }
    if (!file.rename(tmp, out)) die(paste0("Cannot write catalog ", out))
  }, error = function(e) {
    unlink(tmp)
    die(conditionMessage(e))
  })

  summary <- sprintf("catalog prepared from %d file(s), %d record(s)",
                     length(args$contigs), length(records))
  if (skipped > 0L) {
    summary <- paste0(summary, sprintf(" (skipped %d shorter than %d bp)", skipped, min_length))
  }
  cat(summary, "\n", sep = "")
}

main()
