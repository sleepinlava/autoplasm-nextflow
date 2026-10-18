#!/usr/bin/env Rscript
# Build consensus plasmid calls across detection tools.
#
# Pipeline step ``plasmid_consensus``. Strategies: intersection,
# majority_vote, weighted_vote (default), single_tool (primary tool = geNomad).
#
# geNomad is mandatory; additional tool outputs are passed via repeated
# ``--extra`` arguments and are identified by filename pattern:
# ``*.plasme.tsv``, ``*.plasx.tsv``, ``*.platon.tsv``, ``*.scapp.fasta``.
#
# The consensus table follows the plasmidEC ensemble schema
# (github.com/lisavader/plasmidEC, maintained at gitlab.com/mmb-umcu/plasmidEC):
# one row per contig, one fixed column per detection tool
# (genomad/plasme/plasx/platon/scapp) holding that tool's call
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
ENSEMBLE_TOOLS <- c("genomad", "plasme", "plasx", "platon", "scapp")

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

parse_generic_predictions <- function(path, tool_id) {
  dt <- sniff_table(path)
  out <- empty_calls()
  if (nrow(dt) == 0L) return(out)
  fields <- names(dt)
  id_col <- pick_column(fields, ID_COLUMNS)
  if (is.null(id_col)) id_col <- fields[1L]
  score_col <- pick_column(fields, SCORE_COLUMNS)
  class_col <- pick_column(fields, CLASS_COLUMNS)
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
  tryCatch(
    readDNAStringSet(path),
    error = function(e) die(paste0("Cannot read FASTA ", path, ": ", conditionMessage(e)))
  )
}

fasta_ids <- function(dss) {
  vapply(names(dss), function(h) {
    h <- trimws(h)
    sub("[[:space:]].*$", "", h)
  }, character(1), USE.NAMES = FALSE)
}

parse_scapp <- function(path) {
  dss <- read_fasta_dss(path)
  ids <- fasta_ids(dss)
  list(score = as.list(stats::setNames(rep(1.0, length(ids)), ids)),
       is_plasmid = as.list(stats::setNames(rep(TRUE, length(ids)), ids)))
}

identify_extra <- function(path) {
  name <- tolower(basename(path))
  if (grepl(".plasme.", name, fixed = TRUE)) return("plasme")
  if (grepl(".plasx.", name, fixed = TRUE)) return("plasx")
  if (grepl(".platon.", name, fixed = TRUE)) return("platon")
  if (grepl(".scapp.", name, fixed = TRUE) || grepl("confident_cycs", name, fixed = TRUE)) return("scapp")
  NULL
}

parse_weights <- function(spec) {
  weights <- list()
  if (is.null(spec)) return(weights)
  for (item in strsplit(spec, ",", fixed = TRUE)[[1L]]) {
    if (grepl(":", item, fixed = TRUE)) {
      key <- trimws(sub(":.*$", "", item))
      val <- suppressWarnings(as.numeric(trimws(sub("^[^:]*:", "", item))))
      if (!is.na(val)) weights[[key]] <- val
    }
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
    out_fasta = list(mode = "single", required = TRUE, default = NULL),
    out_predictions = list(mode = "single", required = TRUE, default = NULL),
    out_consensus = list(mode = "single", required = TRUE, default = NULL)
  )
  args <- parse_cli(commandArgs(trailingOnly = TRUE), spec)

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
  for (extra in args$extra) {
    tool <- identify_extra(extra)
    if (is.null(tool)) {
      cat(paste0("warning: unrecognized extra prediction file ", extra, "\n"), file = stderr())
      next
    }
    if (tool == "scapp") {
      calls[[tool]] <- parse_scapp(extra)
    } else {
      calls[[tool]] <- parse_generic_predictions(extra, tool)
    }
  }

  weights <- parse_weights(args$weights)
  active <- names(calls)
  all_contigs <- unique(unlist(lapply(calls, function(c) names(c$score)), use.names = FALSE))
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
        sprintf("%.4g", sc[[cid]]),
        if (isTRUE(calls[[tool]]$is_plasmid[[cid]])) "plasmid" else "chromosome",
        fmt_len(info), fmt_gc(info)
      )
    }
  }
  pred_df <- rows_to_df(pred_rows, c("contig_id", "sample_id", "tool_id", "plasmid_score",
                                     "classification", "length", "gc_content"))
  write_tsv(pred_df, args$out_predictions)

  total_weight <- sum(vapply(active, function(t) weight_of(weights, t), numeric(1)))
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
    # geNomad/Platon/SCAPP, absence of a call is a chromosome call);
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
