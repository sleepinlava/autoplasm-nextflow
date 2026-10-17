#!/usr/bin/env Rscript
# DESeq2 differential plasmid abundance between groups.
#
# Aligned with the nf-core/modules deseq2_differential template and the
# DESeq2 vignette: ONE DESeq() fit on the full design (~ group) over all
# shared samples (vignette FAQ: run samples from all groups together, then
# use the contrast argument), vignette prefiltering
# (rowSums(counts(dds) >= 10) >= smallest group size; the script early-exits
# with an empty output when the smallest group has < 3 samples or when no
# row survives), explicit independentFiltering = TRUE + Benjamini-Hochberg
# in results(), and --sf-type to choose the size-factor estimator
# ("poscounts" is the documented remedy for mostly-zero tables).
#
# lfcShrink is standard practice but intentionally SKIPPED here: ashr is
# not installed, and apeglm supports coef = only (no contrast vectors).
#
# Output schema: plasmid_id, group_a, group_b, log2_fold_change, p_value,
# q_value, method, warnings (NA values are written as empty cells).

args <- commandArgs(trailingOnly = TRUE)

arg_value <- function(flag, default = NULL) {
  index <- match(flag, args)
  if (is.na(index)) {
    if (!is.null(default)) return(default)
    stop(paste("Missing", flag))
  }
  if (index == length(args)) stop(paste("Missing value for", flag))
  args[[index + 1]]
}

abundance_path <- arg_value("--abundance")
metadata_path <- arg_value("--metadata")
output_path <- arg_value("--output")
sf_type <- arg_value("--sf-type", "ratio")
if (!(sf_type %in% c("ratio", "poscounts"))) {
  stop(sprintf("Invalid --sf-type '%s' (choose from 'ratio', 'poscounts')", sf_type))
}

output_columns <- c(
  "plasmid_id", "group_a", "group_b", "log2_fold_change",
  "p_value", "q_value", "method", "warnings"
)
empty_output <- function() {
  dir.create(dirname(output_path), recursive = TRUE, showWarnings = FALSE)
  write.table(
    setNames(data.frame(matrix(ncol = length(output_columns), nrow = 0)), output_columns),
    output_path,
    sep = "\t",
    quote = FALSE,
    row.names = FALSE
  )
}

abundance <- read.delim(abundance_path, check.names = FALSE, stringsAsFactors = FALSE)
metadata <- read.delim(metadata_path, check.names = FALSE, stringsAsFactors = FALSE)
if (!all(c("sample_id", "plasmid_id") %in% names(abundance)) ||
    !all(c("sample_id", "group") %in% names(metadata))) {
  stop("Required columns are missing from abundance or metadata input")
}

use_raw_counts <- "raw_count" %in% names(abundance) && any(nzchar(abundance$raw_count))
value_column <- if (use_raw_counts) "raw_count" else "coverage"
if (!value_column %in% names(abundance)) {
  empty_output()
  quit(status = 0)
}
abundance$value <- suppressWarnings(as.numeric(abundance[[value_column]]))
abundance$value[is.na(abundance$value)] <- 0
abundance$value <- round(pmax(abundance$value, 0))

counts <- xtabs(value ~ plasmid_id + sample_id, data = abundance)
metadata <- metadata[!is.na(metadata$group) & nzchar(metadata$group), c("sample_id", "group")]
metadata <- metadata[!duplicated(metadata$sample_id), ]
shared <- intersect(colnames(counts), metadata$sample_id)
if (length(shared) == 0 || nrow(counts) == 0) {
  empty_output()
  quit(status = 0)
}
counts <- counts[, shared, drop = FALSE]
metadata <- metadata[match(shared, metadata$sample_id), , drop = FALSE]
metadata$group <- factor(metadata$group)
if (nlevels(metadata$group) < 2) {
  empty_output()
  quit(status = 0)
}

smallest_group_size <- min(table(metadata$group))
if (smallest_group_size < 3) {
  # Template guard: not enough replication for a stable per-group fit.
  empty_output()
  quit(status = 0)
}

suppressPackageStartupMessages(library(DESeq2))
dds <- DESeqDataSetFromMatrix(
  countData = counts,
  colData = data.frame(group = metadata$group, row.names = metadata$sample_id),
  design = ~ group
)
# Vignette prefilter: keep features with at least 10 counts (the
# size-factor estimator's resolution floor) in at least smallestGroupSize
# samples.
keep <- rowSums(counts(dds) >= 10) >= smallest_group_size
if (!any(keep)) {
  empty_output()
  quit(status = 0)
}
dds <- dds[keep, ]
dds <- DESeq(dds, quiet = TRUE, sfType = sf_type)

cov_warn <- if (use_raw_counts) "" else "Rounded coverage used as count proxy"
groups <- levels(metadata$group)
all_results <- list()
comparison_index <- 1
for (left_index in seq_len(length(groups) - 1)) {
  for (right_index in seq.int(left_index + 1, length(groups))) {
    group_a <- groups[[left_index]]
    group_b <- groups[[right_index]]
    frame <- tryCatch({
      result <- results(dds, contrast = c("group", group_a, group_b),
                        independentFiltering = TRUE, pAdjustMethod = "BH")
      data.frame(
        plasmid_id = rownames(result),
        group_a = group_a,
        group_b = group_b,
        log2_fold_change = result$log2FoldChange,
        p_value = result$pvalue,
        q_value = result$padj,
        method = "DESeq2",
        warnings = cov_warn,
        stringsAsFactors = FALSE
      )
    }, error = function(e) {
      # Edge guard: a failed pairwise contrast (e.g. all-zero counts in the
      # compared groups) yields NA values plus a warning, never a crash.
      data.frame(
        plasmid_id = rownames(dds),
        group_a = group_a,
        group_b = group_b,
        log2_fold_change = NA_real_,
        p_value = NA_real_,
        q_value = NA_real_,
        method = "DESeq2",
        warnings = trimws(paste(cov_warn, paste0("contrast failed: ", conditionMessage(e)))),
        stringsAsFactors = FALSE
      )
    })
    all_results[[comparison_index]] <- frame
    comparison_index <- comparison_index + 1
  }
}

combined <- do.call(rbind, all_results)
dir.create(dirname(output_path), recursive = TRUE, showWarnings = FALSE)
write.table(combined, output_path, sep = "\t", quote = FALSE, row.names = FALSE,
            na = "")
