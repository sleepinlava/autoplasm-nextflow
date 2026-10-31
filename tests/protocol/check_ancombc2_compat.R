#!/usr/bin/env Rscript
# Read the installed upstream function and evaluate only its formula reduction;
# no model fitting, namespace mutation or worker processes are launched.
suppressPackageStartupMessages(library(ANCOMBC))
source('bin/ancombc2_compat.R')
original <- getFromNamespace('.ancombc_global_LRT','ANCOMBC')
patched <- ancombc2_reduced_test(original)
steps <- Filter(function(expr) is.call(expr) && as.character(expr[[1]]) %in% c('=','<-') &&
    identical(expr[[2]],as.name('reduce_fix_formula')),as.list(body(patched))[-1])
stopifnot(length(steps)==2)
cases <- list('group + batch', 'batch + group', 'group + group_batch', 'group_batch + group', 'group')
result <- lapply(cases,function(rhs) {
  context <- list2env(list(fix_formula=rhs,group='group'),parent=baseenv())
  # These assignments precede the upstream model formula construction.
  for(step in steps)eval(step,context)
  reduced <- context$reduce_fix_formula
  vars <- all.vars(as.formula(paste('y ~',reduced,'+ (1 | subject)')))
  stopifnot(!'group' %in% vars)
  if(grepl('group_batch',rhs,fixed=TRUE))stopifnot('group_batch' %in% vars)
  if(grepl('batch',rhs,fixed=TRUE) && !grepl('group_batch',rhs,fixed=TRUE))stopifnot('batch' %in% vars)
  list(formula=rhs,reduced=reduced)
})
cat(jsonlite::toJSON(result,auto_unbox=TRUE,pretty=TRUE),'\n')
