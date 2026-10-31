# Shared explicit design checks; never silently drop metadata rows.
analysis_design <- function(meta, formula, block=NULL) {
  rhs <- sub('^~', '', formula)
  f <- as.formula(paste('~', rhs))
  vars <- unique(c(all.vars(f), block))
  if (!all(vars %in% names(meta))) stop('Design fields missing: ', paste(setdiff(vars,names(meta)),collapse=', '))
  for (v in vars) {
    if (any(is.na(meta[[v]]) | trimws(as.character(meta[[v]])) %in% c('', 'NA')))
      stop('Missing design metadata: ',v)
    if (is.character(meta[[v]])) meta[[v]] <- factor(meta[[v]])
  }
  x <- model.matrix(f,meta)
  if (qr(x)$rank != ncol(x)) stop('Design matrix is rank deficient')
  if (nrow(x) <= ncol(x)) stop('Design has no residual degrees of freedom')
  list(metadata=meta, formula=f, rhs=rhs, variables=vars)
}
