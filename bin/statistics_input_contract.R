# Shared sample/feature identity checks. Numeric validation belongs to consumers.
# Missing sample-feature measurements are not biological zeroes.
statistics_input_contract <- function(abundance, metadata, feature_column, location) {
  fail <- function(message) stop(paste0(location, ": ", message), call. = FALSE)
  if (!"sample_id" %in% names(metadata)) fail("metadata missing sample_id")
  samples <- as.character(metadata[["sample_id"]])
  if (!length(samples) || any(is.na(samples) | !nzchar(trimws(samples)))) fail("metadata needs nonempty sample IDs")
  if (anyDuplicated(samples)) fail("duplicate metadata sample_id")
  if (!all(c("sample_id", feature_column) %in% names(abundance))) fail("missing sample/feature identity columns")
  observed <- as.character(abundance[["sample_id"]])
  features <- as.character(abundance[[feature_column]])
  if (any(is.na(observed) | !nzchar(trimws(observed))) || any(is.na(features) | !nzchar(trimws(features))))
    fail("empty sample or feature ID")
  if (anyDuplicated(data.frame(sample = observed, feature = features))) fail("duplicate sample-feature measurement")
  if (length(observed)) {
    if (!setequal(unique(observed), samples)) fail("abundance/metadata sample set mismatch; missing measurements are not zero")
    if (length(observed) != length(samples) * length(unique(features))) fail("incomplete sample-feature rectangle; missing measurements are not zero")
  }
  list(samples = sort(samples), features = sort(unique(features)))
}
