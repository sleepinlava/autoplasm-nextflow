# ANCOMBC 2.8's reduced-model parser misses a leading group term. Keep
# covariates such as group_batch intact while removing the actual group term.
ancombc2_reduced_test <- function(test) {
  replace_pattern <- function(expr) {
    if (identical(expr,quote(paste0("\\+\\s*",group))))
      return(quote(paste0('(^|\\+)\\s*',group,'\\b')))
    if (is.call(expr)) for(i in seq_along(expr)) expr[[i]] <- replace_pattern(expr[[i]])
    expr
  }
  body(test) <- replace_pattern(body(test))
  test
}
