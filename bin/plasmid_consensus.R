#!/usr/bin/env Rscript
# Build consensus plasmid calls across detection tools.
#
# Pipeline step ``plasmid_consensus``. Strategies: intersection,
# majority_vote, weighted_vote (default), single_tool (primary tool = geNomad).
#
# geNomad is mandatory; additional tool outputs are passed via repeated
# ``--extra`` arguments and are identified by filename pattern:
# ``*.plasme.tsv``, ``*.plasx.tsv``, ``*.platon.tsv``.
#
# The consensus table follows the plasmidEC ensemble schema
# (github.com/lisavader/plasmidEC, maintained at gitlab.com/mmb-umcu/plasmidEC):
# one row per contig, one fixed column per detection tool
# (genomad/plasme/plasx/platon) holding that tool's call
# (``plasmid``/``chromosome``/``NA`` when the tool is disabled), plus
# ``plasmid_count`` (number of tools calling the contig a plasmid) and
# ``combined_prediction`` (plain majority vote). The ``plasmid_call`` column
# keeps the configured consensus strategy (e.g. weighted_vote) and decides
# which contigs are written to the output FASTA.

suppressPackageStartupMessages({
  library(Biostrings)
  library(data.table)
})

ID_COLUMNS <- c("contig_id", "contig", "seq_name", "sequence", "qseqid", "id", "name", "ID")
SCORE_COLUMNS <- c("plasmid_score", "plasme_score", "plasx_score", "score", "probability", "prob")
CLASS_COLUMNS <- c("classification", "prediction", "label", "class", "verdict")
POSITIVE_LABELS <- c("plasmid", "1", "true", "yes", "positive", "plas")
NEGATIVE_LABELS <- c("chromosome", "chromosomal", "0", "false", "no", "negative",
                     "non plasmid", "not plasmid")
METHOD_CHOICES <- c("intersection", "majority_vote", "weighted_vote", "single_tool")
DEFAULT_WEIGHTS <- "genomad:0.6,platon:0.15,plasme:0.15,plasx:0.1"
# Fixed ensemble column order in the consensus table (plasmidEC-style); a
# tool that did not run gets "NA" in its column.
ENSEMBLE_TOOLS <- c("genomad", "plasme", "plasx", "platon")

die <- function(msg) {
  cat(msg, "\n", file = stderr(), sep = "")
  quit(save = "no", status = 2L, runLast = FALSE)
}

py_repr <- function(x) {
  if (grepl("'", x, fixed = TRUE) && !grepl('"', x, fixed = TRUE)) paste0('"', x, '"') else paste0("'", x, "'")
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

count_char <- function(s, ch) {
  nchar(s) - nchar(gsub(ch, "", s, fixed = TRUE))
}

sniff_table <- function(path) {
  lines <- readLines(path, warn = FALSE)
  text <- paste(lines, collapse = "\n")
  if (!nzchar(trimws(text))) return(data.table())
  first <- lines[[1L]]
  delimiter <- if (count_char(first, ",") > count_char(first, "\t")) "," else "\t"
  fread(text = text, sep = delimiter, colClasses = "character",
        stringsAsFactors = FALSE, na.strings = NULL)
}

pick_column <- function(fieldnames, candidates) {
  lowered <- tolower(fieldnames)
  for (cand in candidates) {
    idx <- match(tolower(cand), lowered)
    if (!is.na(idx)) return(fieldnames[idx])
  }
  NULL
}

parse_classification <- function(value, tool_id, path, line_number) {
  if (is.null(value) || is.na(value)) value <- ""
  normalized <- tolower(trimws(value))
  normalized <- gsub("[[:space:]_-]+", " ", normalized)
  if (normalized %in% POSITIVE_LABELS) return(TRUE)
  if (normalized %in% NEGATIVE_LABELS) return(FALSE)
  die(sprintf("Unsupported classification label %s from %s at %s:%d",
              py_repr(value), tool_id, path, line_number))
}

to_score <- function(x) {
  if (is.null(x) || is.na(x) || !nzchar(trimws(x))) return(1.0)
  v <- suppressWarnings(as.numeric(x))
  if (is.na(v)) 1.0 else v
}

empty_calls <- function() list(score = list(), is_plasmid = list())

# PlasX emits every contig with a probability, not a positive-only collection.
# Fixed upstream README recommends score > 0.5; equality is not positive.
parse_plasx <- function(path) {
  dt <- sniff_table(path)
  if (!all(c("contig", "score") %in% names(dt)))
    die(paste0("PlasX predictions require contig and score columns: ", path))
  ids <- trimws(dt$contig)
  check_unique_ids(ids, path, "PlasX prediction data")
  out <- empty_calls()
  for (i in seq_len(nrow(dt))) {
    cid <- ids[i]
    if (is.na(cid) || !nzchar(cid))
      die(sprintf("Empty PlasX contig ID at %s:%d", path, i + 1L))
    score <- suppressWarnings(as.numeric(dt$score[i]))
    if (!is.finite(score) || score < 0 || score > 1)
      die(sprintf("Invalid PlasX score %s at %s:%d: expected a finite probability in [0,1]",
                  py_repr(dt$score[i]), path, i + 1L))
    out$score[[cid]] <- score
    out$is_plasmid[[cid]] <- score > 0.5
  }
  out
}

check_unique_ids <- function(ids, path, kind) {
  nonempty <- which(!is.na(ids) & nzchar(ids))
  repeated <- anyDuplicated(ids[nonempty])
  if (repeated) {
    second <- nonempty[repeated]
    first <- match(ids[second], ids)
    die(sprintf("Duplicate ID '%s' in %s: %s record %d; first seen at record %d",
                ids[second], path, kind, second, first))
  }
}

parse_generic_predictions <- function(path, tool_id) {
  dt <- sniff_table(path)
  out <- empty_calls()
  if (nrow(dt) == 0L) return(out)
  fields <- names(dt)
  id_col <- pick_column(fields, ID_COLUMNS)
  if (is.null(id_col)) id_col <- fields[1L]
  score_col <- pick_column(fields, SCORE_COLUMNS)
  class_col <- pick_column(fields, CLASS_COLUMNS)
  check_unique_ids(trimws(dt[[id_col]]), path, "prediction data")
  for (i in seq_len(nrow(dt))) {
    cid <- trimws(dt[[id_col]][i])
    if (!nzchar(cid)) next
    score <- if (!is.null(score_col)) to_score(dt[[score_col]][i]) else 1.0
    if (!is.null(class_col)) {
      is_plasmid <- parse_classification(dt[[class_col]][i], tool_id, path, i + 1L)
    } else {
      is_plasmid <- TRUE
    }
    out$score[[cid]] <- score
    out$is_plasmid[[cid]] <- is_plasmid
  }
  out
}

parse_genomad <- function(path) {
  dt <- sniff_table(path)
  out <- empty_calls()
  if (nrow(dt) == 0L) return(out)
  fields <- names(dt)
  id_col <- pick_column(fields, "seq_name")
  if (is.null(id_col)) id_col <- fields[1L]
  score_col <- pick_column(fields, "plasmid_score")
  check_unique_ids(trimws(dt[[id_col]]), path, "geNomad data")
  for (i in seq_len(nrow(dt))) {
    cid <- trimws(dt[[id_col]][i])
    if (!nzchar(cid)) next
    score <- if (!is.null(score_col)) to_score(dt[[score_col]][i]) else 1.0
    out$score[[cid]] <- score
    out$is_plasmid[[cid]] <- TRUE
  }
  out
}

read_fasta_dss <- function(path) {
  dss <- tryCatch(
    readDNAStringSet(path),
    error = function(e) die(paste0("Cannot read FASTA ", path, ": ", conditionMessage(e)))
  )
  check_unique_ids(fasta_ids(dss), path, "FASTA")
  empty <- which(width(dss) == 0L)
  if (length(empty) > 0L)
    die(sprintf("Empty FASTA sequence '%s' in %s record %d",
                fasta_ids(dss)[empty[1L]], path, empty[1L]))
  dss
}

fasta_ids <- function(dss) {
  vapply(names(dss), function(h) {
    h <- trimws(h)
    sub("[[:space:]].*$", "", h)
  }, character(1), USE.NAMES = FALSE)
}

identify_extra <- function(path) {
  name <- tolower(basename(path))
  # Sample IDs may contain tool names; only the producer's final suffix identifies it.
  if (grepl("\\.plasme\\.(tsv|csv)(\\.gz)?$", name)) return("plasme")
  if (grepl("\\.plasx\\.(tsv|csv)(\\.gz)?$", name)) return("plasx")
  if (grepl("\\.platon\\.(tsv|csv)(\\.gz)?$", name)) return("platon")
  if (grepl("\\.scapp\\.(fa|fna|fasta)(\\.gz)?$", name) ||
      grepl("(^|[._-])confident_cycs\\.(fa|fna|fasta)(\\.gz)?$", name))
    die(paste0("SCAPP support has been removed; unsupported prediction source: ", path))
  NULL
}

parse_weights <- function(spec) {
  weights <- list()
  if (is.null(spec) || !nzchar(trimws(spec))) return(weights)
  if (grepl("(^|,)[[:space:]]*(,|$)", spec))
    die(paste0("Invalid consensus weights: empty item in ", py_repr(spec)))
  for (item in strsplit(spec, ",", fixed = TRUE)[[1L]]) {
    parts <- strsplit(item, ":", fixed = TRUE)[[1L]]
    if (count_char(item, ":") != 1L || length(parts) != 2L)
      die(paste0("Invalid consensus weights: expected tool:value in ", py_repr(item)))
    key <- trimws(parts[1L])
    if (key == "scapp") die("SCAPP support has been removed; remove scapp from consensus weights")
    if (!key %in% ENSEMBLE_TOOLS)
      die(paste0("Invalid consensus weights: unknown tool in ", py_repr(item)))
    if (key %in% names(weights))
      die(paste0("Invalid consensus weights: duplicate tool in ", py_repr(item)))
    val <- suppressWarnings(as.numeric(trimws(parts[2L])))
    if (!is.finite(val) || val < 0)
      die(paste0("Invalid consensus weights: expected finite nonnegative value in ", py_repr(item)))
    weights[[key]] <- val
  }
  weights
}

weight_of <- function(weights, tool) {
  w <- weights[[tool]]
  if (is.null(w)) 1.0 else w
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

write_tsv <- function(df, path) {
  write.table(df, file = path, sep = "\t", quote = FALSE, row.names = FALSE,
              col.names = TRUE)
}

main <- function() {
  spec <- list(
    assembly = list(mode = "single", required = TRUE, default = NULL),
    genomad_summary = list(mode = "single", required = TRUE, default = NULL),
    extra = list(mode = "multi", append = TRUE, default = character(0)),
    method = list(mode = "single", default = "weighted_vote"),
    weights = list(mode = "single", default = DEFAULT_WEIGHTS),
    sample_id = list(mode = "single", default = ""),
    include_all_contigs = list(mode = "single", default = "false"),
    out_fasta = list(mode = "single", required = TRUE, default = NULL),
    out_predictions = list(mode = "single", required = TRUE, default = NULL),
    out_consensus = list(mode = "single", required = TRUE, default = NULL)
  )
  args <- parse_cli(commandArgs(trailingOnly = TRUE), spec)
  if (!(args$include_all_contigs %in% c("true", "false")))
    die("--include-all-contigs must be true or false")

  method <- args$method
  if (!(method %in% METHOD_CHOICES)) {
    die(sprintf("argument --method: invalid choice: %s (choose from %s)",
                py_repr(method), paste(sprintf("'%s'", METHOD_CHOICES), collapse = ", ")))
  }

  dss <- read_fasta_dss(args$assembly)
  ids <- fasta_ids(dss)
  widths <- width(dss)
  gc_counts <- as.numeric(letterFrequency(dss, "GC")[, "G|C"])
  gcs <- ifelse(widths == 0L, 0.0, gc_counts / widths)
  contig_info <- list()
  for (i in seq_along(ids)) {
    contig_info[[ids[i]]] <- list(length = widths[i], gc = gcs[i])
  }

  calls <- list()
  calls[["genomad"]] <- parse_genomad(args$genomad_summary)
  sources <- list(genomad = args$genomad_summary)
  for (extra in args$extra) {
    tool <- identify_extra(extra)
    if (is.null(tool)) {
      cat(paste0("warning: unrecognized extra prediction file ", extra, "\n"), file = stderr())
      next
    }
    if (tool %in% names(sources)) {
      die(sprintf("Duplicate prediction source for tool %s: %s; first source %s",
                  tool, extra, sources[[tool]]))
    }
    sources[[tool]] <- extra
    calls[[tool]] <- if (tool == "plasx") parse_plasx(extra) else parse_generic_predictions(extra, tool)
  }

  for (tool in names(calls)) {
    unresolved <- setdiff(names(calls[[tool]]$score), ids)
    if (length(unresolved) > 0L)
      die(sprintf("Unresolved prediction ID '%s' from %s at %s: not found in assembly sequences",
                  unresolved[1L], tool, sources[[tool]]))
  }

  weights <- parse_weights(args$weights)
  active <- names(calls)
  total_weight <- sum(vapply(active, function(t) weight_of(weights, t), numeric(1)))
  if (method == "weighted_vote" && (!is.finite(total_weight) || total_weight <= 0))
    die(sprintf("Invalid consensus weights: active total must be finite and positive for weighted_vote (active: %s; specification: %s)",
                paste(active, collapse = ","), py_repr(args$weights)))
  all_contigs <- unique(unlist(lapply(calls, function(c) names(c$score)), use.names = FALSE))
  # The graph-node caller separately verifies the complete geNomad assessment
  # domain. Apply the same voting rule to every input node in that branch.
  if (args$include_all_contigs == "true") all_contigs <- ids
  if (is.null(all_contigs)) all_contigs <- character(0)
  all_contigs <- sort(all_contigs, method = "radix")

  fmt_gc <- function(info) if (is.null(info)) "" else sprintf("%.4f", info$gc)
  fmt_len <- function(info) if (is.null(info)) "" else as.character(info$length)

  pred_rows <- list()
  for (tool in active) {
    sc <- calls[[tool]]$score
    sc_ids <- names(sc)
    if (is.null(sc_ids)) sc_ids <- character(0)
    for (cid in sort(sc_ids, method = "radix")) {
      info <- contig_info[[cid]]
      pred_rows[[length(pred_rows) + 1L]] <- c(
        cid, args$sample_id, tool,
        sprintf(if (tool == "plasx") "%.17g" else "%.4g", sc[[cid]]),
        if (isTRUE(calls[[tool]]$is_plasmid[[cid]])) "plasmid" else "chromosome",
        fmt_len(info), fmt_gc(info)
      )
    }
  }
  pred_df <- rows_to_df(pred_rows, c("contig_id", "sample_id", "tool_id", "plasmid_score",
                                     "classification", "length", "gc_content"))
  write_tsv(pred_df, args$out_predictions)

  n_active <- length(active)

  cons_rows <- list()
  n_plasmid <- 0L
  for (cid in all_contigs) {
    supporting <- character(0)
    conflicting <- character(0)
    for (t in active) {
      pm <- calls[[t]]$is_plasmid
      if (cid %in% names(pm) && isTRUE(pm[[cid]])) supporting <- c(supporting, t) else conflicting <- c(conflicting, t)
    }
    if (method == "intersection") {
      call <- length(supporting) == n_active
    } else if (method == "majority_vote") {
      call <- length(supporting) > n_active / 2
    } else if (method == "single_tool") {
      pm <- calls[["genomad"]]$is_plasmid
      call <- cid %in% names(pm) && isTRUE(pm[[cid]])
    } else {
      w <- sum(vapply(supporting, function(t) weight_of(weights, t), numeric(1)))
      call <- if (total_weight > 0) (w / total_weight) >= 0.5 else FALSE
    }
    if (call) n_plasmid <- n_plasmid + 1L
    info <- contig_info[[cid]]
    # plasmidEC-style ensemble cells: every active tool reports either
    # "plasmid" or "chromosome" (for positive-only outputs such as
    # geNomad/Platon, absence of a call is a chromosome call);
    # disabled tools keep "NA".
    ensemble <- vapply(ENSEMBLE_TOOLS, function(t) {
      if (!(t %in% names(calls))) return("NA")
      pm <- calls[[t]]$is_plasmid
      if (cid %in% names(pm) && isTRUE(pm[[cid]])) "plasmid" else "chromosome"
    }, character(1))
    cons_rows[[length(cons_rows) + 1L]] <- c(
      cid, args$sample_id,
      if (call) "plasmid" else "chromosome",
      paste(supporting, collapse = ";"),
      paste(conflicting, collapse = ";"),
      method,
      fmt_len(info), fmt_gc(info),
      as.character(length(supporting)),
      if (length(supporting) > n_active / 2) "plasmid" else "chromosome",
      ensemble
    )
  }
  cons_df <- rows_to_df(cons_rows, c("contig_id", "sample_id", "plasmid_call", "supporting_tools",
                                     "conflicting_tools", "consensus_method", "length", "gc_content",
                                     "plasmid_count", "combined_prediction", ENSEMBLE_TOOLS))
  write_tsv(cons_df, args$out_consensus)

  keep <- unique(cons_df$contig_id[cons_df$plasmid_call == "plasmid"])
  keep_idx <- which(ids %in% keep)
  if (length(keep_idx) > 0L) {
    out <- dss[keep_idx]
    names(out) <- ids[keep_idx]
    writeXStringSet(out, args$out_fasta, width = 80L)
  } else {
    file.create(args$out_fasta)
  }

  cat(sprintf("consensus: %d/%d contigs called plasmid (%s, tools: %s)\n",
              n_plasmid, nrow(cons_df), method, paste(active, collapse = ", ")))
}

main()
