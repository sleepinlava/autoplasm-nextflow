# Independent official API oracle: read a wide count matrix directly, avoiding
# the production long-table importer, cohort guard and status implementation.
args <- commandArgs(TRUE)
suppressPackageStartupMessages(library(DESeq2))
stopifnot(as.character(packageVersion('DESeq2')) == '1.42.0')
x <- read.delim(args[1],row.names=1,check.names=FALSE,na.strings=NULL)
x <- as.matrix(x)
storage.mode(x) <- 'integer'
m <- read.delim(args[2],colClasses='character',check.names=FALSE,na.strings=NULL)
m <- m[!is.na(m$group) & nzchar(m$group) & m$group != 'NA',,drop=FALSE]
x <- x[,m$sample_id,drop=FALSE]
m$group <- factor(m$group)
keep <- rowSums(x >= 10) >= min(table(m$group))
x <- x[keep,,drop=FALSE]
dds <- DESeqDataSetFromMatrix(x,data.frame(group=m$group,row.names=m$sample_id),~group)
dds <- DESeq(dds,quiet=TRUE,sfType=if(length(args)>3) args[4] else 'ratio')
pairs <- combn(levels(m$group),2,simplify=FALSE)
frames <- lapply(pairs,function(g) {
 r <- results(dds,contrast=c('group',g),independentFiltering=TRUE,pAdjustMethod='BH')
 data.frame(plasmid_id=rownames(r),group_a=g[1],group_b=g[2],
            log2_fold_change=r$log2FoldChange,p_value=r$pvalue,q_value=r$padj)
})
write.table(do.call(rbind,frames),args[3],sep='\t',quote=TRUE,qmethod='double',row.names=FALSE,na='')
