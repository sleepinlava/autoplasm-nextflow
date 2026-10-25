#!/usr/bin/env Rscript
# Generate the AutoPlasm summary report (Markdown + HTML + methods + JSON).
#
# Pipeline step ``report_markdown``: validates explicit current-run inputs,
# summarizes per-sample consensus/circular candidates, and lists observed
# producer outputs. Published directories are never read.
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
  "the assembly graph or read support. The circular count represents candidates, ",
  "not confirmed topology. Terminal inverted repeats alone do not establish ",
  "circularity; an unsupported call has unknown topology, not confirmed linearity. ",
  "TETRA composition scores are not host assignments; uncalibrated TETRA host links ",
  "are disabled after the source-host benchmark failed acceptance.")

# Reporting has no published-directory discovery mode. Every measurement is
# an explicit current-execution input, with sample membership checked first.
read_tsv <- function(path, required) {
  if (!file.exists(path) || dir.exists(path)) die(paste0("Missing report input: ", path))
  rec <- tryCatch(read.delim(path, stringsAsFactors = FALSE, colClasses = "character",
                            na.strings = NULL, quote = "", comment.char = "", check.names = FALSE),
                  error = function(e) die(paste0(path, ": ", conditionMessage(e))))
  if (anyDuplicated(names(rec))) die(paste0(path, ": duplicate TSV columns"))
  if (!all(required %in% names(rec))) die(paste0(path, ": missing required columns"))
  rec
}

fasta_ids <- function(path) {
  con <- file(path, "rt")
  on.exit(close(con))
  ids <- character(0)
  active <- FALSE
  has_sequence <- FALSE
  repeat {
    chunk <- readLines(con, n = 10000L, warn = FALSE)
    if (!length(chunk)) break
    for (line in chunk) {
      if (!nzchar(trimws(line))) next
      if (startsWith(line, ">")) {
        if (active && !has_sequence) die(paste0(path, ": empty FASTA record"))
        name <- strsplit(trimws(substring(line, 2)), "[[:space:]]+")[[1L]][1L]
        if (is.na(name) || !nzchar(name)) die(paste0(path, ": empty FASTA ID"))
        ids[length(ids) + 1L] <- name
        active <- TRUE
        has_sequence <- FALSE
      } else {
        if (!active || !grepl("^[ACGTRYSWKMBDHVNacgtryswkmbdhvn]+$", trimws(line)))
          die(paste0(path, ": malformed FASTA sequence"))
        has_sequence <- TRUE
      }
    }
  }
  if (active && !has_sequence) die(paste0(path, ": empty FASTA record"))
  if (anyDuplicated(ids)) die(paste0(path, ": duplicate FASTA ID"))
  ids
}

spec <- list(
  manifest = list(required = TRUE),
  samplesheet = list(required = TRUE),
  "out-prefix" = list(default = "."),
  template = list(default = "")
)
opts <- parse_args(commandArgs(trailingOnly = TRUE), spec)
manifest <- tryCatch(jsonlite::fromJSON(opts$manifest, simplifyVector = FALSE),
                     error = function(e) die(paste0("Invalid report manifest: ", conditionMessage(e))))
if (!identical(manifest$schema_version, 1L) || !is.list(manifest$records) || !is.list(manifest$settings))
  die("Invalid report manifest schema")
settings <- manifest$settings
project_name <- settings$project_name
platform <- settings$platform
if (!is.character(project_name) || length(project_name) != 1L ||
    !is.character(platform) || length(platform) != 1L) die("Report settings require project_name and platform")
metadata <- read_tsv(opts$samplesheet, "sample_id")
expected <- metadata$sample_id
if (!length(expected) || any(!nzchar(expected)) || anyDuplicated(expected))
  die("Report samplesheet requires nonempty unique sample IDs")

section_names <- c("00_basecalling", "01_qc", "02_assembly", "03_assembly_qc", "04_plasmid_detection",
                   "05_plasmid_binning", "06_plasmid_typing", "07_host_prediction",
                   "08_annotation", "09_comparative_genomics", "10_abundance", "11_diversity", "12_network")
records <- manifest$records
required_kinds <- c("plasmid_fasta", "consensus", "structure")
inputs <- list()
for (record in records) {
  if (!is.character(record$kind) || length(record$kind) != 1L ||
      !is.character(record$producer) || length(record$producer) != 1L ||
      !nzchar(record$producer) || !is.character(record$section) || length(record$section) != 1L ||
      !record$section %in% section_names) die("Invalid report event identity/section")
  if (record$kind %in% required_kinds) {
    if (!is.character(record$sample_id) || length(record$sample_id) != 1L || !record$sample_id %in% expected)
      die("Report input has unexpected sample ID")
    files <- unlist(record$files, use.names = FALSE)
    if (length(files) != 1L || !file.exists(files) || dir.exists(files))
      die(paste0("Missing report input for ", record$sample_id, ": ", record$kind))
    key <- paste(record$sample_id, record$kind, sep = "/")
    if (!is.null(inputs[[key]])) die(paste0("Duplicate report input: ", key))
    inputs[[key]] <- files
  } else if (!record$kind %in% c("evidence", "provided_input")) {
    die("Unknown report event kind")
  }
}
samples <- list()
for (sid in expected) {
  paths <- vapply(required_kinds, function(kind) {
    key <- paste(sid, kind, sep = "/")
    if (is.null(inputs[[key]])) die(paste0("Missing report input: ", key))
    inputs[[key]]
  }, character(1))
  ids <- fasta_ids(paths[["plasmid_fasta"]])
  consensus <- read_tsv(paths[["consensus"]], c("contig_id", "sample_id", "plasmid_call", "supporting_tools"))
  structure <- read_tsv(paths[["structure"]], c("sample_id", "plasmid_id", "is_circular"))
  if (any(consensus$sample_id != sid) || any(structure$sample_id != sid))
    die(paste0(sid, ": report table sample identity mismatch"))
  if (any(!consensus$plasmid_call %in% c("plasmid", "chromosome")))
    die(paste0(sid, ": invalid consensus call"))
  if (anyDuplicated(consensus$contig_id) || anyDuplicated(structure$plasmid_id) ||
      any(!nzchar(consensus$contig_id)) || any(!nzchar(structure$plasmid_id)))
    die(paste0(sid, ": duplicate/empty report feature ID"))
  if (!setequal(ids, consensus$contig_id[consensus$plasmid_call == "plasmid"]) ||
      !setequal(ids, structure$plasmid_id)) die(paste0(sid, ": report FASTA/consensus/structure feature mismatch"))
  if (any(!structure$is_circular %in% c("true", "false"))) die(paste0(sid, ": invalid circularity value"))
  hits <- consensus$plasmid_call == "plasmid"
  tools <- sort(unique(unlist(strsplit(consensus$supporting_tools[hits], ";", fixed = TRUE))))
  tools <- tools[!is.na(tools) & nzchar(tools)]
  samples[[sid]] <- list(contigs = length(ids), circular = sum(structure$is_circular == "true"), tools = tools)
}
sections <- stats::setNames(vapply(section_names, function(section) {
  any(vapply(records, function(record) identical(record$section, section), logical(1)))
}, logical(1)), section_names)
section_status <- vapply(section_names, function(section) {
  matching <- Filter(function(record) identical(record$section, section), records)
  if (!length(matching)) return("not_observed")
  if (all(vapply(matching, function(record) identical(record$kind, "provided_input"), logical(1))))
    return("provided_input")
  "observed_outputs"
}, character(1))
# Validate everything before producing any report products.
final_directory <- opts[["out-prefix"]]
dir.create(final_directory, recursive = TRUE, showWarnings = FALSE)
opts[["out-prefix"]] <- tempfile(pattern = ".report-", tmpdir = final_directory)
dir.create(opts[["out-prefix"]])

lines <- c(
  sprintf("# AutoPlasm report — %s", project_name),
  "",
  sprintf("- Platform: `%s`", platform),
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
lines <- c(lines, "Unmarked sections have no recorded output; they may be disabled or gated by empty inputs.")
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

observed_producers <- sort(unique(vapply(records, function(record) record$producer, character(1))))
versions <- Filter(function(record) identical(record$kind, "evidence") &&
                     startsWith(if (is.null(record$output)) "" else record$output, "versions_"), records)
methods <- paste0("# Methods\n\n",
  "This report uses only declared outputs from the current execution.\n",
  "Observed producers (a version/output record is not proof of a biological hit):\n\n",
  paste0("- ", observed_producers, collapse = "\n"), "\n\n",
  "Version evidence as reported by process outputs (some declarations are static, not runtime probes):\n\n",
  if (length(versions)) paste(unique(vapply(versions, function(record) {
    paste0("- ", record$producer, "/", record$output, ": ", jsonlite::toJSON(record$evidence, auto_unbox = TRUE))
  }, character(1))), collapse = "\n") else "- No version evidence recorded.",
  "\n\nRequested settings (configuration, not evidence that a tool ran):\n\n```json\n",
  jsonlite::toJSON(settings, auto_unbox = TRUE, pretty = TRUE), "\n```\n\n",
  "Complete runtime CLI arguments and database/model identities are not recorded for every producer. ",
  "Missing evidence must not be filled from defaults or inferred from directory names.\n")

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
  project_name = project_name,
  platform = platform,
  date = as.character(Sys.Date()),
  samples = samples_df,
  sections = data.frame(name = section_names,
                        present = unname(sections[section_names]),
                        status = unname(section_status),
                        stringsAsFactors = FALSE),
  input_manifest_md5 = unname(tools::md5sum(opts$manifest)),
  samplesheet_md5 = unname(tools::md5sum(opts$samplesheet)),
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
                      params = list(project_name = project_name,
                                    platform = platform,
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
    sprintf("<title>AutoPlasm report — %s</title>", html_escape(project_name)),
    "<style>body{font-family:sans-serif;max-width:60em;margin:2em auto}</style>",
    sprintf("</head><body><pre>%s</pre></body></html>\n", html_escape(md)))
  write_char(html, file.path(opts[["out-prefix"]], "report.html"))
}

write_char(methods, file.path(opts[["out-prefix"]], "methods.md"))
for (name in c("report.md", "report.html", "methods.md", "report_data.json")) {
  if (!file.rename(file.path(opts[["out-prefix"]], name), file.path(final_directory, name)))
    die(paste0("Could not publish report product: ", name))
}
unlink(opts[["out-prefix"]], recursive = TRUE)
cat("report generated: report.md, report.html, methods.md\n")
