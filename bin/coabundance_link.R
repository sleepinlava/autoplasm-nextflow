#!/usr/bin/env Rscript
# Correlate plasmid coverage with species-level MetaPhlAn profiles.
#
# NOTE on compositionality: MetaPhlAn reports relative abundances, which are
# compositional (closure to a constant sum induces spurious correlation).
# Treat every reported correlation as exploratory. For compositional-rigorous
# inference, run FastSpar (Watts et al. 2019, mSystems; bootstrap p-values with
# BH-FDR) externally on absolute abundances, or clr-transform before testing.
#
# Following the PlasX/MobMess conventions (Yu, Fogarty & Eren 2024, ISME J;
# plasmid-taxon co-occurrence signals are typically weak), each pair is scored
# with the correlation plus a Jaccard presence/absence index, and a p-value
# from stats::cor.test is BH-adjusted (stats::p.adjust) over ALL tested pairs -
# adjustment happens before the |r| filter because the tested hypothesis set
# is every plasmid x taxon pair.

PROG <- "coabundance_link.R"
USAGE <- paste(
  "usage: coabundance_link.R [-h] --plasmid-abundance PLASMID_ABUNDANCE",
  "--host-profiles [HOST_PROFILES ...]",
  "[--host-sample-ids [HOST_SAMPLE_IDS ...]] [--method {spearman,pearson}]",
  "[--min-correlation MIN_CORRELATION] [--max-qvalue MAX_QVALUE] --out OUT"
)

die <- function(msg) {
  cat(sprintf("%s: error: %s\n", PROG, msg), file = stderr())
  quit(save = "no", status = 2L)
}

parse_cli <- function(argv) {
  spec <- list(
    "plasmid-abundance" = list(mode = "single", required = TRUE),
    "host-profiles" = list(mode = "multi", required = TRUE),
    "host-sample-ids" = list(mode = "multi", required = FALSE),
    "method" = list(mode = "single", required = FALSE),
    "min-correlation" = list(mode = "single", required = FALSE),
    "max-qvalue" = list(mode = "single", required = FALSE),
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
  if (!("method" %in% seen)) values[["method"]] <- "spearman"
  if (!("min-correlation" %in% seen)) values[["min-correlation"]] <- "0.6"
  if (!("max-qvalue" %in% seen)) values[["max-qvalue"]] <- "1.0"
  if (!("host-sample-ids" %in% seen)) values[["host-sample-ids"]] <- NULL
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

cell_at <- function(cells, idx) {
  if (idx <= length(cells)) cells[idx] else ""
}

load_plasmid_abundance <- function(path) {
  lines <- tryCatch(
    readLines(path, warn = FALSE),
    error = function(e) die(sprintf("Cannot read plasmid abundance TSV %s: %s",
                                    path, conditionMessage(e)))
  )
  if (length(lines) == 0L || !nzchar(lines[1L])) {
    die(sprintf("%s: missing TSV header", path))
  }
  fields <- split_tsv(lines[1L])
  stripped <- trimws(fields)
  id_col <- if ("plasmid_id" %in% stripped) {
    which(stripped == "plasmid_id")[1L]
  } else if ("contig_id" %in% stripped) {
    which(stripped == "contig_id")[1L]
  } else {
    NA_integer_
  }
  sample_col <- if ("sample_id" %in% stripped) which(stripped == "sample_id")[1L] else NA_integer_
  coverage_col <- if ("coverage" %in% stripped) which(stripped == "coverage")[1L] else NA_integer_
  missing <- c("plasmid_id/contig_id", "sample_id", "coverage")[
    c(is.na(id_col), is.na(sample_col), is.na(coverage_col))]
  if (length(missing)) {
    die(sprintf("%s: expected merged abundance TSV columns; missing %s",
                path, paste(missing, collapse = ", ")))
  }
  plasmids <- list()
  seen <- list()
  for (li in tail(seq_along(lines), -1L)) {
    line <- lines[li]
    if (!nzchar(line)) next
    cells <- split_tsv(line)
    cid <- trimws(cell_at(cells, id_col))
    sample <- trimws(cell_at(cells, sample_col))
    if (!nzchar(cid) || !nzchar(sample)) {
      die(sprintf("%s:%d: empty plasmid ID or sample_id", path, li))
    }
    cov <- suppressWarnings(as.numeric(trimws(cell_at(cells, coverage_col))))
    if (is.na(cov) && !is.nan(cov)) {
      die(sprintf("%s:%d: invalid coverage value", path, li))
    }
    if (!is.finite(cov) || cov < 0) {
      die(sprintf("%s:%d: coverage must be finite and non-negative", path, li))
    }
    key <- paste(cid, sample, sep = "\r")
    if (!is.null(seen[[key]])) {
      die(sprintf("%s:%d: duplicate ('%s', '%s'); first seen on line %d",
                  path, li, sample, cid, seen[[key]]))
    }
    seen[[key]] <- li
    if (is.null(plasmids[[cid]])) plasmids[[cid]] <- list()
    plasmids[[cid]][[sample]] <- cov
  }
  plasmids
}

inferred_profile_id <- function(path) {
  name <- basename(path)
  suffix <- ".metaphlan.tsv"
  if (endsWith(name, suffix)) {
    substr(name, 1L, nchar(name) - nchar(suffix))
  } else {
    sub("\\.[^.]*$", "", name)
  }
}

load_host_profiles <- function(paths, sample_ids) {
  if (length(sample_ids) != length(paths)) {
    die(sprintf("received %d host sample ID(s) for %d profile(s)",
                length(sample_ids), length(paths)))
  }
  if (any(!nzchar(trimws(sample_ids)))) {
    die("host profile sample IDs must not be empty")
  }
  if (anyDuplicated(sample_ids)) {
    die("duplicate host profile sample IDs")
  }
  taxa <- list()
  valid_samples <- character(0)
  for (pi in seq_along(paths)) {
    path <- paths[pi]
    sample <- sample_ids[pi]
    lines <- tryCatch(
      readLines(path, warn = FALSE),
      error = function(e) die(sprintf("Cannot read MetaPhlAn profile %s: %s",
                                      path, conditionMessage(e)))
    )
    header <- NULL
    clade_index <- NA_integer_
    abundance_index <- NA_integer_
    for (li in seq_along(lines)) {
      row <- split_tsv(lines[li])
      if (length(row) == 0L || all(!nzchar(trimws(row)))) next
      first <- trimws(row[1L])
      normalized <- trimws(row)
      normalized[1L] <- trimws(sub("^#+", "", normalized[1L]))
      if ("clade_name" %in% normalized && "relative_abundance" %in% normalized) {
        header <- normalized
        clade_index <- match("clade_name", normalized)
        abundance_index <- match("relative_abundance", normalized)
        next
      }
      if (startsWith(first, "#")) next
      if (is.null(header)) {
        die(sprintf("%s:%d: missing clade_name/relative_abundance header", path, li))
      }
      if (length(row) <= max(clade_index, abundance_index) - 1L) {
        die(sprintf("%s:%d: row has fewer columns than its header", path, li))
      }
      clade <- trimws(row[clade_index])
      parts <- strsplit(clade, "|", fixed = TRUE)[[1L]]
      terminal <- if (length(parts)) parts[length(parts)] else ""
      if (!startsWith(terminal, "s__") || terminal == "s__") next
      abundance <- suppressWarnings(as.numeric(trimws(row[abundance_index])))
      if (is.na(abundance) && !is.nan(abundance)) {
        die(sprintf("%s:%d: invalid relative_abundance", path, li))
      }
      if (!is.finite(abundance) || abundance < 0) {
        die(sprintf("%s:%d: relative_abundance must be finite and non-negative", path, li))
      }
      if (!is.null(taxa[[clade]]) && sample %in% names(taxa[[clade]])) {
        die(sprintf("%s:%d: duplicate species row '%s' for sample '%s'",
                    path, li, clade, sample))
      }
      if (is.null(taxa[[clade]])) taxa[[clade]] <- list()
      taxa[[clade]][[sample]] <- abundance
    }
    if (is.null(header)) {
      die(sprintf("%s: missing clade_name/relative_abundance header", path))
    }
    valid_samples <- c(valid_samples, sample)
  }
  list(samples = valid_samples, taxa = taxa)
}

correlation_value <- function(x, y, method) {
  if (length(unique(x)) < 2L || length(unique(y)) < 2L) {
    return(0)
  }
  suppressWarnings(stats::cor(x, y, method = method))
}

# Method-matched p-value (stats::cor.test on the same vectors that produced
# the score). Untestable pairs (constant vectors, cor.test failure) get p = 1.
correlation_pvalue <- function(x, y, method) {
  if (length(unique(x)) < 2L || length(unique(y)) < 2L) {
    return(1)
  }
  ct <- tryCatch(
    suppressWarnings(stats::cor.test(x, y, method = method)),
    error = function(e) NULL
  )
  if (is.null(ct) || !is.finite(ct$p.value)) 1 else ct$p.value
}

# PlasX/MobMess-style presence/absence score over the shared samples:
# presence = value > 0; jaccard = |intersection| / |union| (0 if union empty).
jaccard_index <- function(x, y) {
  px <- x > 0
  py <- y > 0
  union <- px | py
  if (!any(union)) 0 else sum(px & py) / sum(union)
}

run <- function(args) {
  method <- args[["method"]]
  if (!(method %in% c("spearman", "pearson"))) {
    die(sprintf("argument --method: invalid choice: '%s' (choose from 'spearman', 'pearson')",
                method))
  }
  min_correlation <- parse_float(args[["min-correlation"]], "--min-correlation")
  max_qvalue <- parse_float(args[["max-qvalue"]], "--max-qvalue")
  if (!is.finite(max_qvalue) || max_qvalue < 0 || max_qvalue > 1) {
    die("--max-qvalue must be between 0 and 1")
  }

  plasmids <- load_plasmid_abundance(args[["plasmid-abundance"]])
  if (is.null(args[["host-sample-ids"]])) {
    sample_ids <- vapply(args[["host-profiles"]], inferred_profile_id, character(1))
  } else {
    sample_ids <- args[["host-sample-ids"]]
  }
  profiles <- load_host_profiles(args[["host-profiles"]], sample_ids)
  plasmid_samples <- unique(unlist(lapply(plasmids, names), use.names = FALSE))
  if (is.null(plasmid_samples)) plasmid_samples <- character(0)
  samples <- sort(intersect(plasmid_samples, profiles$samples), method = "radix")

  tested <- list()
  if (length(samples) >= 3L) {
    taxa_ids <- names(profiles$taxa)
    if (is.null(taxa_ids)) taxa_ids <- character(0)
    for (cid in sort(names(plasmids), method = "radix")) {
      profile <- plasmids[[cid]]
      pv_raw <- vapply(samples, function(s) {
        if (!is.null(profile[[s]])) profile[[s]] else 0
      }, numeric(1))
      pv <- if (method == "spearman") rank(pv_raw, ties.method = "average") else pv_raw
      for (taxon in sort(taxa_ids, method = "radix")) {
        tprofile <- profiles$taxa[[taxon]]
        tv_raw <- vapply(samples, function(s) {
          if (!is.null(tprofile[[s]])) tprofile[[s]] else 0
        }, numeric(1))
        tv <- if (method == "spearman") rank(tv_raw, ties.method = "average") else tv_raw
        tested[[length(tested) + 1L]] <- list(
          plasmid_id = cid,
          taxon = taxon,
          correlation = correlation_value(pv, tv, method),
          pvalue = correlation_pvalue(pv, tv, method),
          jaccard = jaccard_index(pv_raw, tv_raw)
        )
      }
    }
  }
  # BH-adjust over ALL tested pairs: the tested hypothesis set is every
  # plasmid x taxon pair, so adjustment precedes the |r| filter.
  qvalues <- if (length(tested)) {
    stats::p.adjust(vapply(tested, function(t) t$pvalue, numeric(1)), method = "BH")
  } else {
    numeric(0)
  }

  rows <- list()
  for (ti in seq_along(tested)) {
    t <- tested[[ti]]
    if (isTRUE(abs(t$correlation) >= min_correlation) && qvalues[ti] <= max_qvalue) {
      rows[[length(rows) + 1L]] <- c(
        t$plasmid_id, t$taxon, paste(samples, collapse = ","), "co_abundance",
        sprintf("%.4f", t$correlation),
        sprintf("method=%s;n_samples=%d;pvalue=%.3g;qvalue=%.3g;jaccard=%.3f",
                method, length(samples), t$pvalue, qvalues[ti], t$jaccard)
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
  cat(sprintf(
    "plasmid samples: %d; valid host profiles: %d; shared samples: %d; links: %d\n",
    length(plasmid_samples), length(profiles$samples), length(samples), nrow(df)
  ), file = stderr())
}

main <- function() {
  args <- parse_cli(commandArgs(trailingOnly = TRUE))
  run(args)
}

main()
