#!/usr/bin/env Rscript
# Link plasmid contigs to first-level MAG FASTA files by sequence composition.
#
# Score: TETRA (Teeling et al. 2004, Env. Microbiol. 6(9):938-947), the
# canonical tetranucleotide-signature method also used by pyani. Instead of a
# raw cosine on composition frequencies (which retains compositional bias), the
# z-score math is ported EXACTLY from pyani's MIT-licensed implementation
# (pyani/tetra.py, https://github.com/widdowquinn/pyani): expected frequencies
# from the maximal-order (3rd) Markov model over di/tri-nucleotide counts,
# sd per Teeling's approximation, z = (observed - expected) / sd, with pyani's
# zero-variance fallback. Pairwise similarity is the Pearson correlation
# between the two z-vectors over canonical tetranucleotide classes; undefined
# or zero-variance z-vectors (e.g. homopolymers) yield similarity 0.
#
# This remains a composition-based heuristic linker; it is not a taxonomic or
# whole-genome alignment method.

suppressPackageStartupMessages({
  library(Biostrings)
})

PROG <- "sequence_similarity_link.R"
USAGE <- paste(
  "usage: sequence_similarity_link.R [-h] --plasmid-contigs PLASMID_CONTIGS",
  "[--host-genomes HOST_GENOMES] [--taxonomy TAXONOMY] [--sample-id SAMPLE_ID]",
  "[--min-similarity MIN_SIMILARITY] --out OUT"
)

die <- function(msg) {
  cat(sprintf("%s: error: %s\n", PROG, msg), file = stderr())
  quit(save = "no", status = 2L)
}

parse_cli <- function(argv) {
  spec <- list(
    "plasmid-contigs" = list(mode = "single", required = TRUE),
    "host-genomes" = list(mode = "single", required = FALSE),
    "taxonomy" = list(mode = "single", required = FALSE),
    "sample-id" = list(mode = "single", required = FALSE),
    "min-similarity" = list(mode = "single", required = FALSE),
    "out" = list(mode = "single", required = TRUE)
  )
  values <- list()
  seen <- character(0)
  i <- 1L
  n <- length(argv)
  while (i <= n) {
    tok <- argv[i]
    if (tok == "-h" || tok == "--help") {
      cat(USAGE, "\n")
      quit(save = "no", status = 0L)
    }
    if (!startsWith(tok, "--")) die(sprintf("unrecognized arguments: %s", tok))
    body <- substr(tok, 3L, nchar(tok))
    eq <- regexpr("=", body, fixed = TRUE)
    if (eq > 0L) {
      name <- substr(body, 1L, eq - 1L)
      inline <- substr(body, eq + 1L, nchar(body))
      has_inline <- TRUE
    } else {
      name <- body
      has_inline <- FALSE
    }
    if (!(name %in% names(spec))) die(sprintf("unrecognized arguments: --%s", name))
    if (spec[[name]]$mode == "multi") {
      if (has_inline) {
        values[[name]] <- inline
      } else {
        vals <- character(0)
        j <- i + 1L
        while (j <= n && !startsWith(argv[j], "--")) {
          vals <- c(vals, argv[j])
          j <- j + 1L
        }
        values[[name]] <- vals
        i <- j - 1L
      }
    } else {
      if (has_inline) {
        values[[name]] <- inline
      } else {
        if (i + 1L > n || startsWith(argv[i + 1L], "--")) {
          die(sprintf("argument --%s: expected one argument", name))
        }
        values[[name]] <- argv[i + 1L]
        i <- i + 1L
      }
    }
    seen <- c(seen, name)
    i <- i + 1L
  }
  missing_req <- names(spec)[vapply(names(spec), function(nm) {
    spec[[nm]]$required && !(nm %in% seen)
  }, logical(1))]
  if (length(missing_req)) {
    die(sprintf("the following arguments are required: %s",
                paste(sprintf("--%s", missing_req), collapse = ", ")))
  }
  if (!("host-genomes" %in% seen)) values[["host-genomes"]] <- NULL
  if (!("taxonomy" %in% seen)) values[["taxonomy"]] <- NULL
  if (!("sample-id" %in% seen)) values[["sample-id"]] <- ""
  if (!("min-similarity" %in% seen)) values[["min-similarity"]] <- "0.7"
  values
}

parse_float <- function(txt, flag) {
  value <- suppressWarnings(as.numeric(txt))
  if (is.na(value) && !is.nan(value)) {
    die(sprintf("argument %s: invalid float value: '%s'", flag, txt))
  }
  value
}

split_tsv <- function(line) {
  cells <- strsplit(line, "\t", fixed = TRUE)[[1L]]
  tab <- gregexpr("\t", line, fixed = TRUE)[[1L]]
  n <- if (tab[1L] == -1L) 1L else length(tab) + 1L
  if (length(cells) < n) cells <- c(cells, rep("", n - length(cells)))
  cells
}

first_token <- function(header) {
  strsplit(header, "[[:space:]]+")[[1L]][1L]
}

read_fasta <- function(path) {
  lines <- tryCatch(
    readLines(path, warn = FALSE),
    error = function(e) die(sprintf("Cannot read FASTA %s: %s", path, conditionMessage(e)))
  )
  records <- list()
  name <- NULL
  seqbuf <- character(0)
  flush_record <- function() {
    if (!is.null(name)) {
      records[[length(records) + 1L]] <<- list(name = name, seq = paste(seqbuf, collapse = ""))
    }
  }
  for (li in seq_along(lines)) {
    line <- lines[li]
    if (startsWith(line, ">")) {
      flush_record()
      header <- trimws(substr(line, 2L, nchar(line)))
      if (!nzchar(header)) {
        die(sprintf("%s:%d: empty FASTA header", path, li))
      }
      name <- first_token(header)
      seqbuf <- character(0)
    } else if (nzchar(trimws(line))) {
      if (is.null(name)) {
        die(sprintf("%s:%d: sequence data before FASTA header", path, li))
      }
      seqbuf <- c(seqbuf, trimws(line))
    }
  }
  flush_record()
  records
}

# K-mer spaces and canonical (both-strands, reverse-complement-folded) counts.
# Canonical slot k holds oligonucleotideFrequency(k) + oligonucleotideFrequency(rc(k));
# palindromic words are counted once, non-canonical slots are zero. This matches
# counting every double-stranded window once under min(kmer, revcomp(kmer)).
kmer_space <- function(width) {
  grid <- expand.grid(rep(list(c("A", "C", "G", "T")), width))
  words <- do.call(paste0, unname(as.list(grid[, seq.int(width, 1L)])))
  rc <- match(as.character(reverseComplement(DNAStringSet(words))), words)
  list(words = words, rc = rc, n = length(words), width = width)
}

SPACE2 <- kmer_space(2L)
SPACE3 <- kmer_space(3L)
SPACE4 <- kmer_space(4L)
REP4 <- which(SPACE4$rc >= seq_len(SPACE4$n))
CANON2 <- pmin(seq_len(SPACE2$n), SPACE2$rc)
CANON3 <- pmin(seq_len(SPACE3$n), SPACE3$rc)
TETRA_PREFIX3 <- CANON3[match(substr(SPACE4$words, 1L, 3L), SPACE3$words)]
TETRA_SUFFIX3 <- CANON3[match(substr(SPACE4$words, 2L, 4L), SPACE3$words)]
TETRA_MIDDLE2 <- CANON2[match(substr(SPACE4$words, 2L, 3L), SPACE2$words)]

canonical_counts <- function(clean, space) {
  raw <- as.numeric(oligonucleotideFrequency(DNAString(clean), width = space$width)[space$words])
  canon <- raw + raw[space$rc]
  idx <- seq_len(space$n)
  canon[idx > space$rc] <- 0
  canon[idx == space$rc] <- raw[idx == space$rc]
  canon
}

# TETRA z-scores per Teeling et al. (2004) as implemented by pyani/tetra.py
# (MIT License, (c) 2017-2019 James Hutton Institute / 2019-2024 University of
# Strathclyde): for each tetranucleotide, expected count under the
# maximal-order Markov model E = tri[prefix] * tri[suffix] / di[middle] and
# sd = sqrt(E * (den - tri[prefix]) * (den - tri[suffix]) / den^2) with
# den = di[middle]; z = (observed - E) / sd. pyani's zero-sd fallback
# z = 1 / den^2 applies when sd == 0 and den > 0; undefined expectations
# (den == 0) leave z as NA. Returns the 136 canonical z-scores.
tetra_zscores <- function(seq) {
  clean <- gsub("[^ACGTN]", "N", toupper(seq))
  di <- canonical_counts(clean, SPACE2)
  tri <- canonical_counts(clean, SPACE3)
  tet <- canonical_counts(clean, SPACE4)
  den <- di[TETRA_MIDDLE2]
  tpre <- tri[TETRA_PREFIX3]
  tsuf <- tri[TETRA_SUFFIX3]
  exp <- tpre * tsuf / den
  var <- exp * (den - tpre) * (den - tsuf) / (den * den)
  sdv <- suppressWarnings(sqrt(var))
  z <- suppressWarnings((tet - exp) / sdv)
  zero_sd <- !is.na(sdv) & sdv == 0 & den > 0
  z[zero_sd] <- 1 / (den[zero_sd] * den[zero_sd])
  z[!is.finite(z)] <- NA_real_
  z[REP4]
}

# Pearson correlation between the two z-vectors over their jointly defined
# (finite) canonical slots. Degenerate cases - fewer than two shared defined
# slots, zero variance, or undefined values (e.g. homopolymer sequences where
# the Markov expectations are degenerate) - yield similarity 0.
similarity <- function(z1, z2) {
  ok <- is.finite(z1) & is.finite(z2)
  if (sum(ok) < 2L) return(0)
  r <- suppressWarnings(stats::cor(z1[ok], z2[ok]))
  if (!is.finite(r)) 0 else r
}

load_taxonomy <- function(path) {
  tax <- character(0)
  if (is.null(path)) return(tax)
  lines <- tryCatch(
    readLines(path, warn = FALSE),
    error = function(e) die(sprintf("Cannot read taxonomy TSV %s: %s", path, conditionMessage(e)))
  )
  if (!length(lines)) return(tax)
  header <- split_tsv(lines[1L])
  genome_col <- match("user_genome", header)
  class_col <- match("classification", header)
  for (li in tail(seq_along(lines), -1L)) {
    if (!nzchar(lines[li])) next
    cells <- split_tsv(lines[li])
    if (is.na(genome_col)) next
    genome <- if (genome_col <= length(cells)) cells[genome_col] else ""
    if (!nzchar(genome)) next
    stem <- sub("\\.[^.]*$", "", basename(genome))
    classification <- if (!is.na(class_col) && class_col <= length(cells)) cells[class_col] else ""
    tax[stem] <- classification
  }
  tax
}

mag_candidates <- function(directory) {
  if (!file.exists(directory)) {
    die(sprintf("MAG path does not exist: %s", directory))
  }
  if (!dir.exists(directory)) {
    die(sprintf("MAG path is not a directory: %s", directory))
  }
  entries <- list.files(directory, full.names = TRUE, all.files = TRUE, no.. = TRUE)
  names_only <- basename(entries)
  ord <- order(names_only, method = "radix")
  entries <- entries[ord]
  names_only <- names_only[ord]
  lower <- tolower(names_only)
  is_file <- file.exists(entries) & !dir.exists(entries)
  ext <- tolower(sub("^.*\\.", "", names_only))
  candidates <- entries[is_file & ext %in% c("fa", "fna", "fasta")]
  compressed <- entries[is_file & (endsWith(lower, ".fa.gz") |
                                     endsWith(lower, ".fna.gz") |
                                     endsWith(lower, ".fasta.gz"))]
  if (!length(candidates) && length(compressed)) {
    die(sprintf("Compressed MAG FASTA is not supported yet: %s",
                paste(compressed, collapse = ", ")))
  }
  candidates
}

load_bins <- function(files) {
  features <- list()
  owners <- character(0)
  for (path in files) {
    host_id <- sub("\\.[^.]*$", "", basename(path))
    if (host_id %in% names(owners)) {
      die(sprintf("Duplicate MAG host_id '%s': %s and %s", host_id, owners[host_id], path))
    }
    owners[host_id] <- path
    seq <- paste(vapply(read_fasta(path), function(r) r$seq, character(1)), collapse = "")
    if (nzchar(seq)) {
      features[[host_id]] <- tetra_zscores(seq)
    }
  }
  features
}

run <- function(args) {
  min_similarity <- parse_float(args[["min-similarity"]], "--min-similarity")
  if (!is.finite(min_similarity) || min_similarity < 0 || min_similarity > 1) {
    die("--min-similarity must be between 0 and 1")
  }
  have_mags <- !is.null(args[["host-genomes"]]) && nzchar(args[["host-genomes"]])
  if (have_mags) {
    files <- mag_candidates(args[["host-genomes"]])
    bins <- load_bins(files)
    taxonomy <- load_taxonomy(args[["taxonomy"]])
  } else {
    files <- character(0)
    bins <- list()
    taxonomy <- character(0)
  }

  plasmids <- read_fasta(args[["plasmid-contigs"]])
  participating <- Filter(function(r) nchar(r$seq) >= 1000L, plasmids)
  collected <- list()
  if (length(bins)) {
    for (rec in participating) {
      pz <- tetra_zscores(rec$seq)
      for (bname in names(bins)) {
        score <- similarity(pz, bins[[bname]])
        if (score >= min_similarity) {
          tax_string <- if (bname %in% names(taxonomy)) taxonomy[bname][[1L]] else "NA"
          collected[[length(collected) + 1L]] <- list(
            plasmid_id = rec$name,
            host_id = bname,
            sample_id = args[["sample-id"]],
            score = score,
            supporting_data = sprintf("taxonomy=%s;method=tetra_zscore", tax_string)
          )
        }
      }
    }
  }

  cols <- c("plasmid_id", "host_id", "sample_id", "evidence_type", "score", "supporting_data")
  df <- data.frame(plasmid_id = character(), host_id = character(), sample_id = character(),
                   evidence_type = character(), score = character(), supporting_data = character())
  if (length(collected)) {
    pls <- vapply(collected, function(r) r$plasmid_id, character(1))
    hos <- vapply(collected, function(r) r$host_id, character(1))
    scs <- vapply(collected, function(r) r$score, numeric(1))
    ord <- order(pls, -scs, hos, method = "radix")
    df <- data.frame(
      plasmid_id = pls[ord],
      host_id = hos[ord],
      sample_id = vapply(collected, function(r) r$sample_id, character(1))[ord],
      evidence_type = "sequence_similarity",
      score = sprintf("%.4f", scs[ord]),
      supporting_data = vapply(collected, function(r) r$supporting_data, character(1))[ord],
      stringsAsFactors = FALSE
    )
  }
  tryCatch(
    write.table(df, file = args[["out"]], sep = "\t", quote = FALSE, row.names = FALSE),
    error = function(e) die(conditionMessage(e))
  )
  mag_path <- if (have_mags) args[["host-genomes"]] else "not provided"
  cat(sprintf(
    "MAG path: %s; candidate FASTA files: %d; valid bins: %d; plasmids compared: %d; links: %d%s\n",
    mag_path, length(files), length(bins),
    if (length(bins)) length(participating) else 0L, nrow(df),
    if (!have_mags) "; MAG input not provided" else ""
  ), file = stderr())
}

main <- function() {
  args <- parse_cli(commandArgs(trailingOnly = TRUE))
  run(args)
}

main()
