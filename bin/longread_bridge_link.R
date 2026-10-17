#!/usr/bin/env Rscript
# Count long-read primary/supplementary alignments bridging two contigs.
#
# The reported host identifier is an assembly contig ID. This script does not
# map host contigs to MAG bins.
#
# Conventions follow mature long-read/SV consumers: like Sniffles2 (Smolka
# et al. 2024, Nat Methods; secondary alignments discarded, MAPQ >= 20 by
# default) and pbsv (>= 2 supporting reads, the --min-reads default), and
# like Hi-C plasmid-host linkers (Risely et al. 2024) contact counts are
# normalised by the product of the two contig lengths (strength) and hosts
# are dense-ranked per plasmid instead of being compared on raw counts.

suppressPackageStartupMessages({
  library(Rsamtools)
})

PROG <- "longread_bridge_link.R"
USAGE <- paste(
  "usage: longread_bridge_link.R [-h] --sam SAM --plasmid-contigs PLASMID_CONTIGS",
  "--assembly ASSEMBLY [--sample-id SAMPLE_ID] [--min-reads MIN_READS]",
  "[--min-mapq MIN_MAPQ] [--min-aln-length MIN_ALN_LENGTH] --out OUT"
)

die <- function(msg) {
  cat(sprintf("%s: error: %s\n", PROG, msg), file = stderr())
  quit(save = "no", status = 2L)
}

parse_cli <- function(argv) {
  spec <- list(
    "sam" = list(mode = "single", required = TRUE),
    "plasmid-contigs" = list(mode = "single", required = TRUE),
    "assembly" = list(mode = "single", required = TRUE),
    "sample-id" = list(mode = "single", required = FALSE),
    "min-reads" = list(mode = "single", required = FALSE),
    "min-mapq" = list(mode = "single", required = FALSE),
    "min-aln-length" = list(mode = "single", required = FALSE),
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
  if (!("sample-id" %in% seen)) values[["sample-id"]] <- ""
  if (!("min-reads" %in% seen)) values[["min-reads"]] <- "2"
  if (!("min-mapq" %in% seen)) values[["min-mapq"]] <- "20"
  if (!("min-aln-length" %in% seen)) values[["min-aln-length"]] <- "0"
  values
}

first_token <- function(header) {
  strsplit(header, "[[:space:]]+")[[1L]][1L]
}

read_fasta_lengths <- function(path) {
  lines <- tryCatch(
    readLines(path, warn = FALSE),
    error = function(e) die(sprintf("Cannot read FASTA %s: %s", path, conditionMessage(e)))
  )
  ids <- character(0)
  lens <- integer(0)
  for (li in seq_along(lines)) {
    if (startsWith(lines[li], ">")) {
      header <- trimws(substr(lines[li], 2L, nchar(lines[li])))
      if (!nzchar(header)) {
        die(sprintf("%s:%d: empty FASTA header", path, li))
      }
      ids <- c(ids, first_token(header))
      lens <- c(lens, 0L)
    } else if (length(lens) && nzchar(trimws(lines[li]))) {
      lens[length(lens)] <- lens[length(lens)] + nchar(trimws(lines[li]))
    }
  }
  keep <- !duplicated(ids)
  lens <- lens[keep]
  names(lens) <- ids[keep]
  lens
}

# Aligned (query-consuming) length of one CIGAR string: sum of runs whose op
# is M, = or X. Missing/empty CIGAR ("*") counts as 0 aligned bases.
cigar_aln_length <- function(c) {
  if (is.na(c) || !nzchar(c)) return(0)
  m <- gregexpr("[0-9]+[A-Z=]", c)[[1L]]
  if (m[1L] == -1L) return(0)
  toks <- substring(c, m, m + attr(m, "match.length") - 1L)
  lens <- as.numeric(substr(toks, 1L, nchar(toks) - 1L))
  sum(lens[substr(toks, nchar(toks), nchar(toks)) %in% c("M", "=", "X")])
}

cigar_aln_lengths <- function(cigars) {
  vapply(cigars, cigar_aln_length, numeric(1))
}

split_tsv <- function(line) {
  cells <- strsplit(line, "\t", fixed = TRUE)[[1L]]
  tab <- gregexpr("\t", line, fixed = TRUE)[[1L]]
  n <- if (tab[1L] == -1L) 1L else length(tab) + 1L
  if (length(cells) < n) cells <- c(cells, rep("", n - length(cells)))
  cells
}

# Validate SAM records with the exact same rules and messages as the Python
# implementation (Rsamtools cannot parse malformed records with these
# diagnostics, so structural checks happen before conversion to BAM).
# Also collects reference names: htslib coerces records whose RNAME is missing
# from the @SQ header into unmapped records, which would corrupt flag
# filtering, so parse_sam extends the header for any extra reference names.
validate_sam <- function(path, lines) {
  header_refs <- character(0)
  refs <- character(0)
  for (li in seq_along(lines)) {
    line <- lines[li]
    if (startsWith(line, "@")) {
      if (startsWith(line, "@SQ\t")) {
        fields <- split_tsv(line)
        sn <- fields[substr(fields, 1, 3) == "SN:"]
        if (length(sn)) header_refs <- c(header_refs, substr(sn[1L], 4L, nchar(sn[1L])))
      }
      next
    }
    if (!nzchar(trimws(line))) next
    fields <- split_tsv(line)
    if (length(fields) < 11L) {
      die(sprintf("%s:%d: SAM record has fewer than 11 fields", path, li))
    }
    flag <- suppressWarnings(as.integer(trimws(fields[2L])))
    if (is.na(flag)) {
      die(sprintf("%s:%d: FLAG is not an integer", path, li))
    }
    if (flag < 0L) {
      die(sprintf("%s:%d: FLAG must be non-negative", path, li))
    }
    rname <- fields[3L]
    if (rname != "*") refs <- c(refs, rname)
    if (bitwAnd(flag, 0x4L) != 0L) next
    if (bitwAnd(flag, 0x100L) != 0L) next
    if (bitwAnd(flag, 0x200L) != 0L) next
    if (bitwAnd(flag, 0x400L) != 0L) next
    if (bitwAnd(flag, 0x1L) != 0L) next
    if (rname == "*") {
      die(sprintf("%s:%d: mapped record has no reference name", path, li))
    }
  }
  list(refs = unique(refs), header_refs = unique(header_refs))
}

# Filter accepted records into the Python-compatible buckets, then apply the
# MAPQ (Sniffles2 convention) and aligned-length filters on what remains.
filter_alignments <- function(qname, flag, rname, mapq, aln_len, min_mapq, min_aln_length) {
  n <- length(flag)
  remaining <- rep(TRUE, n)
  counts <- integer(0)
  take <- function(mask) {
    mask[is.na(mask)] <- FALSE
    hit <- remaining & mask
    remaining <<- remaining & !mask
    sum(hit)
  }
  counts["unmapped"] <- take(bitwAnd(flag, 0x4L) != 0L)
  counts["secondary"] <- take(bitwAnd(flag, 0x100L) != 0L)
  counts["qcfail"] <- take(bitwAnd(flag, 0x200L) != 0L)
  counts["duplicate"] <- take(bitwAnd(flag, 0x400L) != 0L)
  counts["paired"] <- take(bitwAnd(flag, 0x1L) != 0L)
  counts["lowmapq"] <- take(mapq < min_mapq)
  counts["shortaln"] <- take(aln_len < min_aln_length)
  counts <- counts[counts > 0L]
  counts <- counts[order(names(counts), method = "radix")]

  list(qname = qname[remaining], flag = flag[remaining], rname = rname[remaining],
       filtered = counts, accepted = sum(remaining))
}

scan_bam <- function(bam_path, input_label) {
  aln <- tryCatch(
    scanBam(bam_path, param = ScanBamParam(what = c("qname", "flag", "rname", "mapq", "cigar")))[[1L]],
    error = function(e) die(sprintf("Cannot read SAM %s: %s", input_label, conditionMessage(e)))
  )
  list(qname = aln$qname, flag = aln$flag, rname = as.character(aln$rname),
       mapq = aln$mapq, aln_len = cigar_aln_lengths(aln$cigar))
}

# Read alignments via Rsamtools: BAM input is scanned directly; plain-text SAM
# is converted to a temporary BAM first because this Rsamtools build refuses
# to scan SAM. The header is extended with any referenced contig missing from
# @SQ so that htslib preserves the records' flags and reference names. After
# the flag buckets, records with MAPQ < min_mapq (Sniffles2 convention,
# default 20) and records whose aligned (query-consuming) CIGAR length is
# below min_aln_length are dropped into the "lowmapq"/"shortaln" buckets.
parse_sam <- function(path, lines, extra_refs, min_mapq, min_aln_length) {
  sam_path <- path
  if (length(extra_refs)) {
    sam_path <- tempfile(fileext = ".sam")
    insert <- sprintf("@SQ\tSN:%s\tLN:2147483647", extra_refs)
    first_rec <- which(!startsWith(lines, "@"))[1L]
    if (is.na(first_rec)) {
      new_lines <- c(lines, insert)
    } else {
      new_lines <- c(lines[seq_len(first_rec - 1L)], insert, lines[first_rec:length(lines)])
    }
    writeLines(new_lines, sam_path)
    on.exit(unlink(sam_path), add = TRUE)
  }
  bam_path <- tryCatch(
    asBam(sam_path, tempfile(fileext = ""), overwrite = TRUE),
    error = function(e) die(sprintf("Cannot read SAM %s: %s", path, conditionMessage(e)))
  )
  on.exit(unlink(c(bam_path, paste0(bam_path, ".bai"))), add = TRUE)
  aln <- scan_bam(bam_path, path)
  filter_alignments(aln$qname, aln$flag, aln$rname, aln$mapq, aln$aln_len,
                    min_mapq, min_aln_length)
}

# Direct BAM path: scanBam streams a BAM without an index; the record-level
# validation from validate_sam() is unnecessary because htslib guarantees
# structural validity of BAM input.
parse_bam <- function(path, min_mapq, min_aln_length) {
  aln <- scan_bam(path, path)
  filter_alignments(aln$qname, aln$flag, aln$rname, aln$mapq, aln$aln_len,
                    min_mapq, min_aln_length)
}

run <- function(args) {
  min_reads_txt <- trimws(args[["min-reads"]])
  if (!grepl("^[+-]?[0-9]+$", min_reads_txt)) {
    die(sprintf("argument --min-reads: invalid int value: '%s'", args[["min-reads"]]))
  }
  min_reads <- as.numeric(min_reads_txt)
  if (min_reads < 1) {
    die("--min-reads must be a positive integer")
  }
  min_mapq_txt <- trimws(args[["min-mapq"]])
  if (!grepl("^[+-]?[0-9]+$", min_mapq_txt)) {
    die(sprintf("argument --min-mapq: invalid int value: '%s'", args[["min-mapq"]]))
  }
  min_mapq <- as.numeric(min_mapq_txt)
  if (min_mapq < 0) {
    die("--min-mapq must be non-negative")
  }
  min_aln_txt <- trimws(args[["min-aln-length"]])
  if (!grepl("^[+-]?[0-9]+$", min_aln_txt)) {
    die(sprintf("argument --min-aln-length: invalid int value: '%s'", args[["min-aln-length"]]))
  }
  min_aln_length <- as.numeric(min_aln_txt)
  if (min_aln_length < 0) {
    die("--min-aln-length must be non-negative")
  }
  plasmid_lengths <- read_fasta_lengths(args[["plasmid-contigs"]])
  assembly_lengths <- read_fasta_lengths(args[["assembly"]])
  plasmid_ids <- names(plasmid_lengths)
  assembly_ids <- names(assembly_lengths)
  is_bam <- function(path) {
    con <- tryCatch(file(path, open = "rb"), error = function(e) NULL)
    if (is.null(con)) return(FALSE)
    on.exit(close(con))
    magic <- tryCatch(readBin(con, "raw", n = 2L), error = function(e) raw(0))
    length(magic) == 2L && magic[1L] == as.raw(0x1f) && magic[2L] == as.raw(0x8b)
  }
  if (is_bam(args[["sam"]])) {
    aln <- parse_bam(args[["sam"]], min_mapq, min_aln_length)
  } else {
    sam_lines <- tryCatch(
      readLines(args[["sam"]], warn = FALSE),
      error = function(e) die(sprintf("Cannot read SAM %s: %s", args[["sam"]], conditionMessage(e)))
    )
    sam_info <- validate_sam(args[["sam"]], sam_lines)
    aln <- parse_sam(args[["sam"]], sam_lines, setdiff(sam_info$refs, sam_info$header_refs),
                     min_mapq, min_aln_length)
  }

  kind <- ifelse(bitwAnd(aln$flag, 0x800L) != 0L, "supplementary", "primary")
  groups <- split(seq_along(aln$qname), aln$qname)
  bridges <- list()
  bridge_reads <- 0L
  for (qn in names(groups)) {
    idx <- groups[[qn]]
    primary <- unique(aln$rname[idx[kind[idx] == "primary"]])
    supplementary <- unique(aln$rname[idx[kind[idx] == "supplementary"]])
    if (!length(primary) || !length(supplementary)) next
    bridge_reads <- bridge_reads + 1L
    targets <- unique(c(primary, supplementary))
    plasmids_hit <- intersect(targets, plasmid_ids)
    hosts_hit <- intersect(setdiff(targets, plasmid_ids), assembly_ids)
    for (p in plasmids_hit) {
      for (h in hosts_hit) {
        key <- paste(p, h, sep = "\r")
        if (is.null(bridges[[key]])) bridges[[key]] <- character(0)
        if (!(qn %in% bridges[[key]])) bridges[[key]] <- c(bridges[[key]], qn)
      }
    }
  }

  rows <- list()
  if (length(bridges)) {
    keys <- names(bridges)
    parts <- strsplit(keys, "\r", fixed = TRUE)
    pls <- vapply(parts, function(x) x[1L], character(1))
    hos <- vapply(parts, function(x) x[2L], character(1))
    ord <- order(pls, hos, method = "radix")
    pls <- pls[ord]
    hos <- hos[ord]
    counts <- vapply(ord, function(ki) length(bridges[[keys[ki]]]), integer(1))
    keep <- counts >= min_reads
    pls <- pls[keep]
    hos <- hos[keep]
    counts <- counts[keep]
    # Hi-C-style normalisation: strength = reads / (plasmid_kb * host_kb),
    # with FASTA lengths from the two inputs; hosts are dense-ranked per
    # plasmid among the emitted hosts by descending raw count (ties share).
    strengths <- mapply(function(p, h, c) {
      c / ((as.numeric(plasmid_lengths[[p]]) / 1000) *
           (as.numeric(assembly_lengths[[h]]) / 1000))
    }, pls, hos, counts)
    host_rank <- integer(length(counts))
    for (p in unique(pls)) {
      idx <- which(pls == p)
      host_rank[idx] <- match(counts[idx], sort(unique(counts[idx]), decreasing = TRUE))
    }
    for (i in seq_along(pls)) {
      rows[[length(rows) + 1L]] <- c(
        pls[i], hos[i], args[["sample-id"]], "long_read_bridge",
        as.character(counts[i]),
        sprintf("bridging_reads=%d;host_id_type=contig;strength=%.4g;host_rank=%d",
                counts[i], strengths[i], host_rank[i])
      )
    }
  }

  cols <- c("plasmid_id", "host_id", "sample_id", "evidence_type", "score", "supporting_data")
  df <- data.frame(plasmid_id = character(), host_id = character(), sample_id = character(),
                   evidence_type = character(), score = character(), supporting_data = character())
  if (length(rows)) {
    m <- do.call(rbind, rows)
    colnames(m) <- cols
    df <- as.data.frame(m, stringsAsFactors = FALSE)
  }
  tryCatch(
    write.table(df, file = args[["out"]], sep = "\t", quote = FALSE, row.names = FALSE),
    error = function(e) die(conditionMessage(e))
  )
  filtered_text <- if (length(aln$filtered)) {
    paste(sprintf("%s=%d", names(aln$filtered), aln$filtered), collapse = ", ")
  } else {
    "none"
  }
  cat(sprintf(
    "SAM: %s; accepted long-read alignments: %d; reads with primary and supplementary records: %d; filtered records: %s; bridges: %d\n",
    args[["sam"]], aln$accepted, bridge_reads, filtered_text, nrow(df)
  ), file = stderr())
}

main <- function() {
  args <- parse_cli(commandArgs(trailingOnly = TRUE))
  run(args)
}

main()
