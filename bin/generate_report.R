#!/usr/bin/env Rscript
# Generate the AutoPlasm summary report (Markdown + HTML + methods + JSON).
#
# Simplified standalone re-implementation of the ABI ``report_markdown``
# node: scans the published results directory, summarizes per-sample plasmid
# counts from the consensus tables, circularity from structure tables, and
# lists the available analysis sections.
#
# Reporting follows the nf-core two-tier pattern (nf-core/differentialabundance):
# a data-collection step emits report_data.json, and report.html is rendered
# from the R Markdown template passed via --template (rmarkdown + pandoc);
# without a template it falls back to a simple pre-formatted HTML page.
# report.md and methods.md are always written with the stable legacy layout.

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

html_escape <- function(s) {
  s <- gsub("&", "&amp;", s, fixed = TRUE)
  s <- gsub("<", "&lt;", s, fixed = TRUE)
  s <- gsub(">", "&gt;", s, fixed = TRUE)
  s <- gsub('"', "&quot;", s, fixed = TRUE)
  s <- gsub("'", "&#x27;", s, fixed = TRUE)
  s
}

WARNING <- paste0(
  "Sequence-based circularity is predictive and should be confirmed from ",
  "the assembly graph or read support.")

count_fasta_records <- function(path) {
  tryCatch(sum(startsWith(readLines(path, warn = FALSE), ">")),
           error = function(e) 0)
}

summarize_consensus <- function(path) {
  total <- 0
  plasmids <- 0
  tools <- character(0)
  tryCatch({
    rec <- read.delim(path, stringsAsFactors = FALSE, quote = "",
                      comment.char = "")
    total <- nrow(rec)
    call <- if ("plasmid_call" %in% names(rec)) as.character(rec$plasmid_call) else character(0)
    hits <- which(call == "plasmid")
    plasmids <- length(hits)
    if ("supporting_tools" %in% names(rec)) {
      st <- as.character(rec$supporting_tools[hits])
      st <- st[!is.na(st)]
      pieces <- unlist(strsplit(st, ";", fixed = TRUE))
      tools <- sort(unique(pieces[nzchar(pieces)]))
    }
  }, error = function(e) NULL)
  list(total = total, plasmids = plasmids, tools = tools)
}

summarize_structure <- function(path) {
  circular <- 0
  tryCatch({
    rec <- read.delim(path, stringsAsFactors = FALSE, quote = "",
                      comment.char = "")
    if ("is_circular" %in% names(rec))
      circular <- sum(as.character(rec$is_circular) == "true")
  }, error = function(e) NULL)
  circular
}

spec <- list(
  outdir = list(required = TRUE),
  platform = list(default = ""),
  "project-name" = list(default = "plasmid_analysis"),
  "out-prefix" = list(default = "."),
  template = list(default = "")
)
opts <- parse_args(commandArgs(trailingOnly = TRUE), spec)

outdir <- opts$outdir
det_dir <- file.path(outdir, "04_plasmid_detection")
samples <- list()
consensus_dir <- file.path(det_dir, "consensus")
structure_dir <- file.path(det_dir, "structure")
if (dir.exists(consensus_dir)) {
  fastas <- sort(list.files(consensus_dir, pattern = "\\.plasmid_contigs\\.fasta$"))
  for (fasta in fastas) {
    sid <- sub("\\.plasmid_contigs\\.fasta.*$", "", fasta)
    entry <- list(contigs = count_fasta_records(file.path(consensus_dir, fasta)),
                  total = 0, plasmids = 0, tools = character(0), circular = 0)
    cons <- file.path(consensus_dir, paste0(sid, ".plasmid_consensus.tsv"))
    if (file.exists(cons)) {
      s <- summarize_consensus(cons)
      entry$total <- s$total
      entry$plasmids <- s$plasmids
      entry$tools <- s$tools
    }
    struct <- file.path(structure_dir, paste0(sid, ".plasmid_structure.tsv"))
    if (file.exists(struct))
      entry$circular <- summarize_structure(struct)
    samples[[sid]] <- entry
  }
}

section_names <- c("01_qc", "02_assembly", "03_assembly_qc", "04_plasmid_detection",
                   "05_plasmid_binning", "06_plasmid_typing", "07_host_prediction",
                   "08_annotation", "09_comparative_genomics", "10_abundance",
                   "11_diversity", "12_network")
sections <- stats::setNames(file.path(outdir, section_names) |>
                              vapply(dir.exists, logical(1)), section_names)

lines <- c(
  sprintf("# AutoPlasm report — %s", opts[["project-name"]]),
  "",
  sprintf("- Platform: `%s`", opts$platform),
  sprintf("- Date: %s", Sys.Date()),
  sprintf("- Samples: %d", length(samples)),
  "",
  "## Plasmid detection summary",
  "",
  "| sample_id | consensus_plasmids | circular | detection_tools |",
  "|---|---|---|---|"
)
for (sid in names(samples)) {
  e <- samples[[sid]]
  lines <- c(lines, sprintf("| %s | %d | %d | %s |", sid, e$contigs,
                            e$circular, paste(e$tools, collapse = ", ")))
}
lines <- c(lines, "", "## Analysis sections", "")
for (nm in section_names)
  lines <- c(lines, sprintf("- %s `%s`", ifelse(sections[nm], "[x]", "[ ]"), nm))
lines <- c(lines, "", "## Limitations", "", sprintf("- %s", WARNING),
           "- Plasmid calls are predictions from automated classifiers; confirm biologically important hits manually.",
           "")
md <- paste(lines, collapse = "\n")

write_char <- function(text, path) {
  con <- file(path, open = "wb")
  on.exit(close(con))
  writeChar(text, con, eos = NULL, useBytes = TRUE)
}
write_char(md, file.path(opts[["out-prefix"]], "report.md"))

methods <- paste0(
  "# Methods\n\n",
  "Metagenomic plasmid analysis was performed with AutoPlasm (Nextflow DSL2 ",
  "implementation). Reads were quality-filtered (fastp for short reads; ",
  "NanoPlot/Filtlong for ONT; HiFiAdapterFilt for PacBio HiFi). Assembly used ",
  "platform-appropriate assemblers (MEGAHIT/metaSPAdes, metaFlye, ",
  "hifiasm-meta, OPERA-MS/hybridSPAdes). Plasmid contigs were detected with ",
  "geNomad and integrated across tools by consensus voting ",
  sprintf("(%s platform). Typing used PlasmidFinder and MOB-typer; ", opts$platform),
  "annotation used Bakta, AMRFinderPlus, ISEScan and IntegronFinder. ",
  "Abundance was estimated with CoverM.\n")

# Machine-readable data layer (consumed by assets/plasmid_report.Rmd and any
# downstream tooling; the nf-core reporting pattern keeps data collection
# separate from rendering).
if (length(samples)) {
  samples_df <- data.frame(
    sample_id = names(samples),
    consensus_plasmids = vapply(samples, function(e) as.integer(e$contigs), integer(1)),
    circular = vapply(samples, function(e) as.integer(e$circular), integer(1)),
    detection_tools = vapply(samples, function(e) paste(e$tools, collapse = ", "), character(1)),
    stringsAsFactors = FALSE
  )
} else {
  samples_df <- data.frame(
    sample_id = character(0), consensus_plasmids = integer(0),
    circular = integer(0), detection_tools = character(0),
    stringsAsFactors = FALSE
  )
}
report_data <- list(
  project_name = opts[["project-name"]],
  platform = opts$platform,
  date = as.character(Sys.Date()),
  samples = samples_df,
  sections = data.frame(name = section_names,
                        present = unname(sections[section_names]),
                        stringsAsFactors = FALSE),
  methods = sub("^# Methods\n\n", "", methods)
)
# Absolute path: rmarkdown knits the template in its own directory context.
# normalizePath only absolutizes existing paths, so resolve the (existing)
# out-prefix directory, then join the file name.
data_json <- file.path(normalizePath(opts[["out-prefix"]], mustWork = TRUE),
                       "report_data.json")
# jsonlite leaks non-default rownames as a "_row" column; reset them first
rownames(report_data$samples) <- NULL
write_char(jsonlite::toJSON(report_data, auto_unbox = TRUE, pretty = TRUE), data_json)

# HTML: rendered from the R Markdown template when available (nf-core-style
# narrative report); otherwise fall back to the simple pre-formatted page.
rendered <- FALSE
if (nzchar(opts$template)) {
  rendered <- tryCatch({
    suppressPackageStartupMessages(library(rmarkdown))
    rmarkdown::render(opts$template,
                      params = list(project_name = opts[["project-name"]],
                                    platform = opts$platform,
                                    data_json = data_json),
                      output_file = "report.html",
                      output_dir = opts[["out-prefix"]],
                      intermediates_dir = tempdir(),
                      quiet = TRUE)
    TRUE
  }, error = function(e) {
    cat(sprintf("warning: rmarkdown render failed (%s); falling back to simple HTML\n",
                conditionMessage(e)), file = stderr())
    FALSE
  })
}
if (!rendered) {
  html <- paste0(
    "<!DOCTYPE html><html><head><meta charset='utf-8'>",
    sprintf("<title>AutoPlasm report — %s</title>", html_escape(opts[["project-name"]])),
    "<style>body{font-family:sans-serif;max-width:60em;margin:2em auto}</style>",
    sprintf("</head><body><pre>%s</pre></body></html>\n", html_escape(md)))
  write_char(html, file.path(opts[["out-prefix"]], "report.html"))
}

write_char(methods, file.path(opts[["out-prefix"]], "methods.md"))
cat("report generated: report.md, report.html, methods.md\n")
