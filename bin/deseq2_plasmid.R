#!/usr/bin/env Rscript
# One DESeq2 fit on the full ~group design, followed by pairwise contrasts.
# Keep the existing >=10 count prefilter, ratio size factors, independent
# filtering and BH correction. Model-ineligible inputs have explicit status;
# missing counts never become zero or coverage-derived pseudo-counts.

script_file <- sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value=TRUE)[1L])
source(file.path(dirname(normalizePath(script_file)), "statistics_input_contract.R"))

parse_arguments <- function(args) {
  allowed <- c("--abundance", "--metadata", "--output", "--out-status",
               "--sf-type", "--min-replicates")
  opts <- list()
  i <- 1L
  while (i <= length(args)) {
    flag <- args[i]
    if (!flag %in% allowed) stop(paste("Unknown argument", flag), call.=FALSE)
    if (!is.null(opts[[flag]])) stop(paste("Duplicate argument", flag), call.=FALSE)
    if (i == length(args) || startsWith(args[i + 1L], "--"))
      stop(paste("Missing value for", flag), call.=FALSE)
    opts[[flag]] <- args[i + 1L]
    i <- i + 2L
  }
  for (flag in c("--abundance", "--metadata", "--output"))
    if (is.null(opts[[flag]])) stop(paste("Missing", flag), call.=FALSE)
  opts
}
opts <- parse_arguments(commandArgs(trailingOnly=TRUE))
abundance_path <- opts[["--abundance"]]
metadata_path <- opts[["--metadata"]]
output_path <- opts[["--output"]]
status_path <- opts[["--out-status"]]
sf_type <- if (is.null(opts[["--sf-type"]])) "ratio" else opts[["--sf-type"]]
if (!sf_type %in% c("ratio", "poscounts"))
  stop("Invalid --sf-type (choose from 'ratio', 'poscounts')", call.=FALSE)
min_replicates <- if (is.null(opts[["--min-replicates"]])) 3 else
  suppressWarnings(as.numeric(opts[["--min-replicates"]]))
if (!is.finite(min_replicates) || min_replicates < 1 ||
    min_replicates != floor(min_replicates) || min_replicates > .Machine$integer.max)
  stop("--min-replicates must be a positive integer within R integer range", call.=FALSE)

abundance <- read.delim(abundance_path, check.names=FALSE, stringsAsFactors=FALSE,
                       colClasses=c(sample_id="character", plasmid_id="character"),
                       na.strings=NULL)
metadata <- read.delim(metadata_path, check.names=FALSE, stringsAsFactors=FALSE,
                      colClasses=c(sample_id="character", group="character"),
                      na.strings=NULL)
missing_abundance <- setdiff(c("sample_id", "plasmid_id", "raw_count"), names(abundance))
if (length(missing_abundance))
  stop(paste0(abundance_path, ": missing required columns: ", paste(missing_abundance, collapse=", ")),
       call.=FALSE)
missing_metadata <- setdiff(c("sample_id", "group"), names(metadata))
if (length(missing_metadata))
  stop(paste0(metadata_path, ": missing required columns: ", paste(missing_metadata, collapse=", ")),
       call.=FALSE)
metadata$group[!is.na(metadata$group) & metadata$group == "NA"] <- NA
abundance$value <- suppressWarnings(as.numeric(abundance$raw_count))
bad <- which(!is.finite(abundance$value) | abundance$value < 0 |
             abundance$value != floor(abundance$value) | abundance$value > .Machine$integer.max)
if (length(bad)) {
  i <- bad[1L]
  stop(sprintf("Invalid numeric value in %s:%d sample=%s feature=%s field=raw_count value='%s'; expected finite nonnegative integer raw count within DESeq2 range; coverage is not a count",
               abundance_path, i + 1L, abundance$sample_id[i], abundance$plasmid_id[i],
               abundance$raw_count[i]), call.=FALSE)
}
identity <- statistics_input_contract(abundance, metadata, "plasmid_id", abundance_path)
# Build an ordinary integer matrix. Subsetting xtabs drops its xtabs class,
# leaving table: as.matrix(table) still retains table in R4.3 and the fixed
# DESeq2/SummarizedExperiment stack loses its dimensions during S4 conversion.
input_counts <- matrix(0L, nrow=length(identity$features), ncol=length(identity$samples),
                       dimnames=list(identity$features, identity$samples))
if (nrow(abundance))
  input_counts[cbind(match(abundance$plasmid_id, identity$features),
                     match(abundance$sample_id, identity$samples))] <- as.integer(abundance$value)
original_metadata <- metadata
metadata <- metadata[!is.na(metadata$group) & nzchar(metadata$group), c("sample_id", "group")]
model_samples <- colnames(input_counts)[colnames(input_counts) %in% metadata$sample_id]
metadata <- metadata[match(model_samples, metadata$sample_id), , drop=FALSE]
metadata$group <- factor(metadata$group)
model_counts <- input_counts[, model_samples, drop=FALSE]
model_fitted <- FALSE
model_version <- "not_loaded"

output_columns <- c("plasmid_id", "group_a", "group_b", "log2_fold_change",
                    "p_value", "q_value", "method", "warnings")
write_results <- function(frame) {
  dir.create(dirname(output_path), recursive=TRUE, showWarnings=FALSE)
  text_fields <- frame[vapply(frame, is.character, logical(1))]
  quote_fields <- any(vapply(text_fields, function(values) any(grepl('[[:cntrl:]"]', values)), logical(1)))
  write.table(frame, output_path, sep="\t", quote=quote_fields, qmethod="double", row.names=FALSE, na="")
}
write_status <- function(state, reason, failed_contrasts=0L) {
  if (!is.null(status_path)) {
    ids <- original_metadata$sample_id
    library_used <- colSums(model_counts)[match(ids, colnames(model_counts))]
    status <- data.frame(
      analysis_status=state, reason=reason, sample_id=ids,
      group=ifelse(is.na(original_metadata$group), "", original_metadata$group),
      in_design=ids %in% model_samples, used_in_fit=model_fitted & ids %in% model_samples,
      input_library_size=unname(colSums(input_counts)[ids]), model_library_size=unname(library_used),
      features_input=nrow(input_counts), features_used=nrow(model_counts),
      min_replicates=min_replicates, sf_type=sf_type, model_fitted=model_fitted,
      deseq2_version=model_version, failed_contrasts=failed_contrasts,
      stringsAsFactors=FALSE, check.names=FALSE)
    dir.create(dirname(status_path), recursive=TRUE, showWarnings=FALSE)
    write.table(status, status_path, sep="\t", quote=TRUE, qmethod="double", row.names=FALSE, na="")
  }
  message(sprintf("DESeq2 status: %s (%s); %d design samples, %d input/%d used features",
                  state, reason, length(model_samples), nrow(input_counts), nrow(model_counts)))
}
no_model <- function(state, reason) {
  write_results(setNames(data.frame(matrix(ncol=length(output_columns), nrow=0)), output_columns))
  write_status(state, reason)
  quit(status=0)
}
if (!nrow(input_counts)) no_model("not_run", "zero_features")
if (nlevels(metadata$group) < 2) no_model("not_run", "insufficient_groups")
smallest_group_size <- min(table(metadata$group))
if (smallest_group_size < min_replicates) no_model("not_run", "insufficient_replication")
if (ncol(model_counts) <= nlevels(metadata$group))
  no_model("not_estimable", "insufficient_residual_degrees_of_freedom")
all_zero <- !any(model_counts > 0)
# The same vignette prefilter as before, applied before constructing DESeqDataSet
# so legitimate all-zero inputs do not hit its deliberate all-zero error.
keep <- rowSums(model_counts >= 10) >= smallest_group_size
model_counts <- model_counts[keep, , drop=FALSE]
if (!nrow(model_counts))
  no_model("not_run", if (all_zero) "all_zero_counts" else "no_features_after_count_filter")
# Never drop these samples or impute a size factor: either estimator is undefined
# for a zero library after filtering. Keep the full cohort visible in status.
if (any(colSums(model_counts) == 0)) no_model("not_estimable", "zero_count_samples")
if (sf_type == "ratio" && !any(rowSums(model_counts == 0) == 0))
  no_model("not_estimable", "no_positive_geometric_means")

suppressPackageStartupMessages(library(DESeq2))
model_version <- as.character(packageVersion("DESeq2"))
dds <- DESeqDataSetFromMatrix(
  countData=model_counts,
  colData=data.frame(group=metadata$group, row.names=metadata$sample_id), design=~group)
dds <- DESeq(dds, quiet=TRUE, sfType=sf_type)
model_fitted <- TRUE
groups <- levels(metadata$group)
all_results <- list()
failed_contrasts <- 0L
for (left_index in seq_len(length(groups) - 1L)) {
  for (right_index in seq.int(left_index + 1L, length(groups))) {
    group_a <- groups[[left_index]]
    group_b <- groups[[right_index]]
    frame <- tryCatch({
      result <- results(dds, contrast=c("group", group_a, group_b),
                        independentFiltering=TRUE, pAdjustMethod="BH")
      data.frame(plasmid_id=rownames(result), group_a=group_a, group_b=group_b,
                 log2_fold_change=result$log2FoldChange, p_value=result$pvalue,
                 q_value=result$padj, method="DESeq2", warnings="", stringsAsFactors=FALSE)
    }, error=function(e) {
      failed_contrasts <<- failed_contrasts + 1L
      data.frame(plasmid_id=rownames(dds), group_a=group_a, group_b=group_b,
                 log2_fold_change=NA_real_, p_value=NA_real_, q_value=NA_real_,
                 method="DESeq2", warnings=paste0("contrast failed: ", conditionMessage(e)),
                 stringsAsFactors=FALSE)
    })
    all_results[[length(all_results) + 1L]] <- frame
  }
}
write_results(do.call(rbind, all_results))
write_status(if (failed_contrasts) "completed_with_contrast_failures" else "completed",
             if (failed_contrasts) "contrast_failure" else "model_fitted", failed_contrasts)
