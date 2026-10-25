#!/usr/bin/env Rscript
# Detect plasmid circularity and terminal overlap.
#
# Pipeline step ``plasmid_structure``. Circularity evidence:
# header-declared markers plus sequence-based direct terminal repeats detected
# with the geNomad convention (genomad/sequence.py has_dtr/has_itr) and
# CheckV's low-complexity filters (CheckV complete_genomes.py
# fetch_dtr/fetch_itr):
#
# * DTR: take the first 21 bp as a seed, find its LAST occurrence in the
#   second half of the sequence (pos >= len/2), extend to the contig end;
#   the sequence is DTR+ iff prefix == suffix exactly.
# * ITR: first 21 bp == reverse complement of the last 21 bp, extendable
#   up to 1000 bp while the prefix == revcomp(suffix) identity holds.
#   ITR is structural repeat evidence, not support for circular topology.
# * Exact matching only (no mismatches). A candidate repeat is rejected as
#   low-complexity when its 21-mer seed occurs > 8 times genome-wide, its
#   N fraction is > 0.2, or its dominant base frequency is > 0.70
#   (CheckV filters); a filtered repeat does NOT confer circularity and is
#   reported with overlap 0. Note this replaces the historical
#   "longest exact prefix/suffix overlap of 20..1000 bp" scan of the
#   Python handler, so a terminal overlap of only 20 bp is no longer
#   considered circular (the terminal-repeat convention now starts at
#   21 bp).

suppressPackageStartupMessages(library(Biostrings))

REPEAT_SEED_LENGTH <- 21L
ITR_MAX_LENGTH <- 1000L
WARNINGS_TEXT <- paste(
  "Sequence-based circularity is predictive and should be confirmed from",
  "the assembly graph or read support."
)
LOW_COMPLEXITY_NOTE <- "low-complexity terminal repeat filtered"
ITR_TOPOLOGY_NOTE <- paste(
  "Terminal inverted repeats alone do not support circular topology;",
  "topology remains unknown, not confirmed linear."
)

header_circularity <- function(header) {
  tokens <- strsplit(tolower(trimws(header)), "[[:space:];]+", perl = TRUE)[[1L]]
  id <- if (length(tokens)) tokens[1L] else ""
  negative_id <- grepl("(^|_)not_circular$", id, perl = TRUE)
  positive <- any(tokens %in% c("circular=true", "topology=circular")) ||
    (grepl("_circular$", id) && !negative_id)
  negative <- negative_id || any(tokens %in% c("not_circular", "circular=false", "topology=linear"))
  list(circular = positive && !negative, conflict = positive && negative)
}

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

revcomp_dna <- function(x) {
  # Base-R reverse complement for IUPAC ACGTN (other chars pass through).
  chartr("ACGTNacgtn", "TGCANtgcan", paste(rev(strsplit(x, "", fixed = TRUE)[[1L]]),
                                          collapse = ""))
}

find_dtr <- function(sequence) {
  # geNomad has_dtr: last occurrence of the 21 bp seed in the second half,
  # extend to the contig end, exact prefix == suffix. Returns repeat length
  # or 0.
  n <- nchar(sequence)
  if (n < 2L * REPEAT_SEED_LENGTH) return(0L)
  seed <- substr(sequence, 1L, REPEAT_SEED_LENGTH)
  hits <- gregexpr(seed, sequence, fixed = TRUE)[[1L]]
  if (hits[1L] == -1L) return(0L)
  half_start <- n %/% 2L + 1L
  hits <- hits[hits >= half_start]
  if (length(hits) == 0L) return(0L)
  start <- max(hits)
  repeat_length <- n - start + 1L
  if (substr(sequence, 1L, repeat_length) ==
      substr(sequence, n - repeat_length + 1L, n)) {
    return(as.integer(repeat_length))
  }
  0L
}

find_itr <- function(sequence) {
  # geNomad has_itr: first 21 bp == revcomp(last 21 bp), extendable up to
  # 1000 bp while prefix == revcomp(suffix). Returns repeat length or 0.
  n <- nchar(sequence)
  if (n < 2L * REPEAT_SEED_LENGTH) return(0L)
  if (substr(sequence, 1L, REPEAT_SEED_LENGTH) !=
      revcomp_dna(substr(sequence, n - REPEAT_SEED_LENGTH + 1L, n))) {
    return(0L)
  }
  max_len <- min(ITR_MAX_LENGTH, n %/% 2L)
  size <- REPEAT_SEED_LENGTH
  while (size < max_len &&
         substr(sequence, 1L, size + 1L) ==
         revcomp_dna(substr(sequence, n - size, n))) {
    size <- size + 1L
  }
  as.integer(size)
}

repeat_low_complexity <- function(sequence, repeat_length) {
  # CheckV filters on the candidate repeat: seed occurs <= 8 times in the
  # whole sequence, N fraction <= 0.2, dominant base frequency <= 0.70.
  n <- nchar(sequence)
  seed <- substr(sequence, 1L, REPEAT_SEED_LENGTH)
  hits <- gregexpr(seed, sequence, fixed = TRUE)[[1L]]
  n_seed <- if (hits[1L] == -1L) 0L else length(hits)
  if (n_seed > 8L) return(TRUE)
  repeat_seq <- substr(sequence, 1L, repeat_length)
  n_n <- nchar(repeat_seq) - nchar(gsub("N", "", repeat_seq, fixed = TRUE))
  if (n_n / nchar(repeat_seq) > 0.2) return(TRUE)
  base_counts <- vapply(c("A", "C", "G", "T"), function(b) {
    nchar(repeat_seq) - nchar(gsub(b, "", repeat_seq, fixed = TRUE))
  }, numeric(1))
  if (max(base_counts) / nchar(repeat_seq) > 0.70) return(TRUE)
  FALSE
}

rows_to_df <- function(rows, header) {
  if (length(rows) == 0L) {
    df <- as.data.frame(matrix(character(0), nrow = 0L, ncol = length(header)),
                        stringsAsFactors = FALSE)
    names(df) <- header
    return(df)
  }
  m <- do.call(rbind, rows)
  colnames(m) <- header
  as.data.frame(m, stringsAsFactors = FALSE)
}

main <- function() {
  spec <- list(
    contigs = list(mode = "single", required = TRUE, default = NULL),
    sample_id = list(mode = "single", default = ""),
    out = list(mode = "single", required = TRUE, default = NULL)
  )
  args <- parse_cli(commandArgs(trailingOnly = TRUE), spec)

  dss <- tryCatch(
    readDNAStringSet(args$contigs),
    error = function(e) die(paste0("Cannot read FASTA ", args$contigs, ": ", conditionMessage(e)))
  )
  headers <- names(dss)
  ids <- vapply(headers, function(h) {
    h <- trimws(h)
    sub("[[:space:]].*$", "", h)
  }, character(1), USE.NAMES = FALSE)
  seqs <- toupper(as.character(dss))
  widths <- width(dss)

  rows <- vector("list", length(seqs))
  for (i in seq_along(seqs)) {
    seq_i <- seqs[i]
    header_evidence <- header_circularity(headers[i])
    dtr_len <- find_dtr(seq_i)
    itr_len <- find_itr(seq_i)
    dtr_ok <- dtr_len > 0L && !repeat_low_complexity(seq_i, dtr_len)
    itr_ok <- itr_len > 0L && !repeat_low_complexity(seq_i, itr_len)
    repeat_types <- c(if (dtr_ok) "dtr", if (itr_ok) "itr")
    repeat_type <- if (length(repeat_types)) paste(repeat_types, collapse = "+") else "none"
    if (header_evidence$circular) {
      is_circular <- TRUE
      method <- "header_marker"
      overlap <- max(dtr_len, itr_len)
      warnings <- WARNINGS_TEXT
    } else if (dtr_ok) {
      is_circular <- TRUE
      method <- "dtr"
      overlap <- dtr_len
      warnings <- WARNINGS_TEXT
    } else if (itr_ok) {
      is_circular <- FALSE
      method <- "itr"
      overlap <- itr_len
      warnings <- ITR_TOPOLOGY_NOTE
    } else {
      is_circular <- FALSE
      method <- "none"
      overlap <- 0L
      # A rejected (low-complexity) terminal repeat is noted explicitly so
      # the raw detection is auditable; otherwise keep the standing warning.
      warnings <- if (dtr_len > 0L || itr_len > 0L) LOW_COMPLEXITY_NOTE else WARNINGS_TEXT
    }
    if (header_evidence$conflict) {
      warnings <- paste(warnings, "conflicting circularity header markers; header inference disabled")
    }
    # The legacy boolean records a supported circularity candidate. A false
    # value never establishes linearity; keep that distinction explicit.
    topology_status <- if (isTRUE(is_circular)) "circular_candidate" else "unknown"
    topology_evidence <- if (isTRUE(is_circular)) method else "none"
    rows[[i]] <- c(
      args$sample_id, ids[i], as.character(widths[i]),
      tolower(as.character(isTRUE(is_circular))),
      as.character(overlap),
      method,
      warnings,
      args$contigs,
      repeat_type,
      topology_status,
      topology_evidence
    )
  }
  df <- rows_to_df(rows, c("sample_id", "plasmid_id", "length_bp", "is_circular",
                           "terminal_overlap_bp", "method", "warnings", "source_file",
                           "repeat_type", "topology_status", "topology_evidence"))
  write.table(df, file = args$out, sep = "\t", quote = FALSE, row.names = FALSE,
              col.names = TRUE)

  cat(sprintf("plasmid structure: %d sequence(s) evaluated\n", length(seqs)))
}

main()
