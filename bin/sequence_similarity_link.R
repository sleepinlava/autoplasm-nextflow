#!/usr/bin/env Rscript
# Score plasmid/MAG sequence composition; uncalibrated host linking is disabled.
#
# TETRA per Teeling et al. (2004), doi:10.1186/1471-2105-5-163:
# sum every overlapping ACGT di/tri/tetranucleotide on BOTH strands of each
# FASTA record separately, then calculate Markov expected counts and z-scores.
# Pearson correlation uses all 256 ordered words, including both RC slots and
# doubled palindromic counts. Records are never joined across contig boundaries.
# This is an independent implementation of the published formula, not an exact
# port of pyani (which has different sequence-end handling and sparse defaults).
# Undefined/zero variance profiles are ineligible, not fabricated correlations.
# No host links are emitted: the independent source-host threshold benchmark
# failed its acceptance criteria. Scores are composition similarities only.

suppressPackageStartupMessages({
  library(Biostrings)
})

PROG <- "sequence_similarity_link.R"
METHOD <- "tetra_markov256_v1"
USAGE <- paste(
  "usage: sequence_similarity_link.R [-h] --plasmid-contigs PLASMID_CONTIGS",
  "[--host-genomes HOST_GENOMES] [--taxonomy TAXONOMY] [--sample-id SAMPLE_ID]",
  "[--min-similarity MIN_SIMILARITY] --out OUT",
  "[--out-scores OUT_SCORES] [--out-profile-status OUT_PROFILE_STATUS]"
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
    "out" = list(mode = "single", required = TRUE),
    "out-scores" = list(mode = "single", required = FALSE),
    "out-profile-status" = list(mode = "single", required = FALSE)
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
  if (!("min-similarity" %in% seen)) values[["min-similarity"]] <- NULL
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

# Ordered word spaces. No canonical folding: reverse complements retain their
# own slot, and palindromes are counted once per physical strand (twice total).
kmer_space <- function(width) {
  grid <- expand.grid(rep(list(c("A", "C", "G", "T")), width))
  words <- do.call(paste0, unname(as.list(grid[, seq.int(width, 1L)])))
  rc <- match(as.character(reverseComplement(DNAStringSet(words))), words)
  list(words = words, rc = rc, n = length(words), width = width)
}
SPACE2 <- kmer_space(2L)
SPACE3 <- kmer_space(3L)
SPACE4 <- kmer_space(4L)
TETRA_PREFIX3 <- match(substr(SPACE4$words, 1L, 3L), SPACE3$words)
TETRA_SUFFIX3 <- match(substr(SPACE4$words, 2L, 4L), SPACE3$words)
TETRA_MIDDLE2 <- match(substr(SPACE4$words, 2L, 3L), SPACE2$words)

strand_counts <- function(sequences, space) {
  counts <- numeric(space$n)
  for (sequence in sequences) {
    clean <- gsub("[^ACGTN]", "N", toupper(sequence))
    raw <- as.numeric(oligonucleotideFrequency(DNAString(clean), width = space$width)[space$words])
    counts <- counts + raw + raw[space$rc]
  }
  stats::setNames(counts, space$words)
}

# E(XYZW) = N(XYZ) N(YZW) / N(YZ)
# Var = E (N(YZ)-N(XYZ)) (N(YZ)-N(YZW)) / N(YZ)^2
# All legal windows including the last one are counted. Ambiguity symbols break
# a window; they are not deleted. Sum per-record counts BEFORE expectations.
tetra_zscores <- function(sequences) {
  di <- strand_counts(sequences, SPACE2)
  tri <- strand_counts(sequences, SPACE3)
  tet <- strand_counts(sequences, SPACE4)
  den <- di[TETRA_MIDDLE2]
  tpre <- tri[TETRA_PREFIX3]
  tsuf <- tri[TETRA_SUFFIX3]
  expected <- tpre * tsuf / den
  variance <- expected * (den - tpre) * (den - tsuf) / (den * den)
  z <- rep(NA_real_, SPACE4$n)
  valid <- is.finite(variance) & variance > 0 & is.finite(expected)
  z[valid] <- (tet[valid] - expected[valid]) / sqrt(variance[valid])
  stats::setNames(z, SPACE4$words)
}

profile_status <- function(z) {
  if (length(z) != 256L || any(!is.finite(z))) return("undefined_markov_variance")
  if (stats::sd(z) == 0) return("constant_zscores")
  "complete256"
}

# A partial finite subset is not the published 256-dimensional comparison.
# No usable profile means no numeric similarity, even at threshold zero.
similarity <- function(z1, z2) {
  if (profile_status(z1) != "complete256" || profile_status(z2) != "complete256") return(NA_real_)
  r <- stats::cor(z1, z2)
  if (!is.finite(r)) NA_real_ else max(-1, min(1, r))
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
    stem <- sub("\\.(fa|fna|fasta)(\\.gz)?$", "", basename(genome), ignore.case = TRUE)
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
  # recursive: Nextflow staging can nest the source directory one level down
  entries <- list.files(directory, full.names = TRUE, all.files = TRUE, no.. = TRUE,
                        recursive = TRUE)
  names_only <- basename(entries)
  ord <- order(names_only, method = "radix")
  entries <- entries[ord]
  names_only <- names_only[ord]
  lower <- tolower(names_only)
  is_file <- file.exists(entries) & !dir.exists(entries)
  ext <- tolower(sub("^.*\\.", "", names_only))
  compressed <- endsWith(lower, ".fa.gz") |
                endsWith(lower, ".fna.gz") |
                endsWith(lower, ".fasta.gz")
  # R file connections auto-detect gzip on read, so .gz FASTAs are fine
  candidates <- entries[is_file & (ext %in% c("fa", "fna", "fasta") | compressed)]
  candidates
}

load_bins <- function(files) {
  features <- list()
  owners <- character(0)
  for (path in files) {
    host_id <- sub("\\.(fa|fna|fasta)(\\.gz)?$", "", basename(path), ignore.case = TRUE)
    if (host_id %in% names(owners)) {
      die(sprintf("Duplicate MAG host_id '%s': %s and %s", host_id, owners[host_id], path))
    }
    owners[host_id] <- path
    sequences <- vapply(read_fasta(path), function(r) r$seq, character(1))
    if (any(nzchar(sequences))) {
      features[[host_id]] <- tetra_zscores(sequences)
    }
  }
  features
}

run <- function(args) {
  if (!is.null(args[["min-similarity"]])) {
    legacy <- parse_float(args[["min-similarity"]], "--min-similarity")
    if (!is.finite(legacy) || legacy < 0 || legacy > 1) die("--min-similarity must be between 0 and 1")
    cat("--min-similarity is deprecated and ignored; uncalibrated host links are disabled\n", file=stderr())
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
  scored <- list()
  plasmid_profiles <- list()
  if (length(bins)) {
    for (rec in participating) {
      pz <- tetra_zscores(rec$seq)
      plasmid_profiles[[rec$name]] <- profile_status(pz)
      for (bname in names(bins)) {
        score <- similarity(pz, bins[[bname]])
        status <- if (is.finite(score)) "complete256" else "ineligible_profile"
        tax_string <- if (bname %in% names(taxonomy)) taxonomy[bname][[1L]] else "NA"
        scored[[length(scored) + 1L]] <- data.frame(plasmid_id = rec$name,
          host_id = bname, sample_id = args[["sample-id"]], method = METHOD,
          score = if (is.finite(score)) sprintf("%.17g", score) else "",
          profile_status = status, host_taxonomy = tax_string,
          threshold_status = "not_applied_uncalibrated",
          association_status = "disabled_uncalibrated", stringsAsFactors = FALSE)
      }
    }
  }

  df <- data.frame(plasmid_id = character(), host_id = character(), sample_id = character(),
                   evidence_type = character(), score = character(), supporting_data = character())
  tryCatch(
    write.table(df, file = args[["out"]], sep = "\t", quote = FALSE, row.names = FALSE),
    error = function(e) die(conditionMessage(e))
  )
  if (!is.null(args[["out-scores"]])) {
    score_table <- if (length(scored)) do.call(rbind, scored) else data.frame(
      plasmid_id=character(), host_id=character(), sample_id=character(), method=character(),
      score=character(), profile_status=character(), host_taxonomy=character(),
      threshold_status=character(), association_status=character())
    if (nrow(score_table)) score_table <- score_table[order(score_table$plasmid_id, score_table$host_id, method="radix"), ]
    write.table(score_table, args[["out-scores"]], sep="\t", quote=FALSE, row.names=FALSE)
  }
  if (!is.null(args[["out-profile-status"]])) {
    jsonlite::write_json(list(method=METHOD, dimensions=256L, strands="both",
      boundaries="sum_per_record_counts_before_expectations",
      threshold_status="not_applied_uncalibrated", host_links_enabled=FALSE,
      association_status="disabled_uncalibrated",
      association_reason="independent source-host threshold benchmark failed acceptance; composition scores are not host assignments",
      ignored_min_similarity=args[["min-similarity"]], ineligible="undefined variance or constant full vector; no fabricated score",
      sample_id=args[["sample-id"]],
      mag_profiles=lapply(bins, profile_status), plasmid_profiles=plasmid_profiles,
      short_plasmids=vapply(Filter(function(r) nchar(r$seq) < 1000L, plasmids), function(r) r$name, character(1))),
      args[["out-profile-status"]], auto_unbox=TRUE, pretty=TRUE)
  }
  cat(sprintf("method=%s; dimensions=256; host_links=disabled_uncalibrated; complete MAG profiles=%d/%d\n",
      METHOD, sum(vapply(bins, profile_status, character(1)) == "complete256"), length(bins)), file=stderr())
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
