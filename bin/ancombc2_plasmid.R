#!/usr/bin/env Rscript
suppressPackageStartupMessages({ library(data.table); library(jsonlite) })
script <- sub('^--file=','',grep('^--file=',commandArgs(FALSE),value=TRUE)[1])
source(file.path(dirname(normalizePath(script)),'statistics_input_contract.R'))
source(file.path(dirname(normalizePath(script)),'statistics_design.R'))
source(file.path(dirname(normalizePath(script)),'ancombc2_compat.R'))
a <- commandArgs(TRUE); opts <- setNames(as.list(a[seq(2,length(a),2)]),sub('^--','',a[seq(1,length(a),2)]))
ab <- fread(opts$abundance,colClasses=c(sample_id='character',plasmid_id='character'),na.strings=NULL)
md <- read.delim(opts$metadata,colClasses=c(sample_id='character'),check.names=FALSE,na.strings=NULL)
ids <- statistics_input_contract(ab,md,'plasmid_id',opts$abundance)
if (!'raw_count' %in% names(ab)) stop('ANCOM-BC2 requires raw_count')
x <- suppressWarnings(as.numeric(ab$raw_count))
if(any(!is.finite(x) | x<0 | x!=floor(x) | x>2^53)) stop('ANCOM-BC2 needs finite exact nonnegative integer counts')
ab[,raw_count:=x]
if (nrow(ab)) {
  wide <- dcast(ab,plasmid_id~sample_id,value.var='raw_count')
  mat <- as.matrix(wide[,-1,with=FALSE]);rownames(mat)<-wide$plasmid_id
  mat <- mat[ids$features,ids$samples,drop=FALSE]
} else mat <- matrix(0,0,length(ids$samples),dimnames=list(character(),ids$samples))
md <- md[match(ids$samples,md$sample_id),,drop=FALSE];rownames(md)<-md$sample_id
nonempty <- colSums(mat)>0
status <- list(status='ineligible',reason='insufficient_nonempty_samples_or_features',excluded_empty=as.list(ids$samples[!nonempty]),
               formula=opts$formula,random_formula=opts$random,prevalence=as.numeric(opts$prevalence),count_unit=unique(ab$count_unit))
dir.create(opts$output)
for (name in c('coefficients','global','pairwise','structural_zeros')) fwrite(data.table(taxon=character()),file.path(opts$output,paste0(name,'.tsv')),sep='\t')
if (sum(nonempty)>=3 && nrow(mat)>0) {
  md <- md[nonempty,,drop=FALSE];mat<-mat[,nonempty,drop=FALSE]
  if (!'group' %in% names(md)) {
    status$reason <- 'no_group_column'
  } else {
  md$group <- factor(md$group)
  if (nlevels(md$group)>=2 && all(table(md$group)>=as.integer(opts$replicates))) {
    rand <- if(nzchar(opts$random)) opts$random else NULL
    rand_vars <- if(is.null(rand)) NULL else all.vars(as.formula(paste('~',rand)))
    design <- analysis_design(md,opts$formula,rand_vars)
    md <- design$metadata
    # Direct matrix + metadata interface from upstream ANCOMBC 2.8.0.
    suppressPackageStartupMessages(library(ANCOMBC))
    set.seed(20261030L)
    multigroup <- nlevels(md$group)>2
    # ANCOMBC 2.8's reduced-model regex misses a leading group term.
    # Fix only that regex in this R process; retain the upstream model/tests.
    if (!is.null(rand) && multigroup) {
      reduced_test <- ancombc2_reduced_test(getFromNamespace('.ancombc_global_LRT','ANCOMBC'))
      assignInNamespace('.ancombc_global_LRT',reduced_test,'ANCOMBC')
      status$compatibility_changes <- 'ANCOMBC 2.8: remove leading group term from reduced mixed model'
    }
    fit <- ANCOMBC::ancombc2(data=mat,meta_data=md,taxa_are_rows=TRUE,
        fix_formula=design$rhs,rand_formula=rand,p_adj_method='BH',
        prv_cut=as.numeric(opts$prevalence),group='group',struc_zero=TRUE,
        pseudo_sens=TRUE,global=multigroup,pairwise=multigroup,n_cl=as.integer(opts$threads),verbose=FALSE)
    for (pair in list(c('res','coefficients'),c('res_global','global'),c('res_pair','pairwise'),c('zero_ind','structural_zeros'))) {
      result <- fit[[pair[1]]]
      if (!is.null(result)) {
        for (term in sub('^lfc_','',grep('^lfc_',names(result),value=TRUE))) {
          result[[paste0('ci_low_',term)]] <- result[[paste0('lfc_',term)]] - qnorm(.975)*result[[paste0('se_',term)]]
          result[[paste0('ci_high_',term)]] <- result[[paste0('lfc_',term)]] + qnorm(.975)*result[[paste0('se_',term)]]
        }
        fwrite(as.data.table(result,keep.rownames=pair[1]=='zero_ind'),file.path(opts$output,paste0(pair[2],'.tsv')),sep='\t')
      }
    }
    status$status <- 'measured';status$reason <- '';status$sample_ids<-as.list(colnames(mat))
    status$tests <- list(coefficients=TRUE,global=multigroup,pairwise=multigroup)
    status$confidence_intervals <- list(level=.95,method='pointwise normal Wald approximation from ANCOMBC standard errors; not simultaneous or multiplicity adjusted')
    status$versions <- c(as.list(sapply(c('ANCOMBC','CVXR','lme4','Matrix'),function(p) as.character(packageVersion(p)))),list(R=R.version.string))
  } else status$reason <- 'insufficient_group_replicates'
  }
}
write_json(status,file.path(opts$output,'status.json'),pretty=TRUE,auto_unbox=TRUE)
