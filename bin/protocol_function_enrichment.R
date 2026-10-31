#!/usr/bin/env Rscript
suppressPackageStartupMessages({library(data.table);library(jsonlite)})
a<-commandArgs(TRUE);functions<-fread(file.path(a[1],'functions.tsv'));membership<-fread(file.path(a[2],'membership.tsv'));all_plasmids<-fread(file.path(a[3],'structure.tsv'))$plasmid_id
presence<-unique(functions[,.(plasmid_id,source,term)])
result<-data.table(system_id=character(),source=character(),term=character(),odds_ratio=numeric(),p_value=numeric(),q_value=numeric())
for(s in unique(membership$system_id[nzchar(membership$system_id)])) {
  members<-unique(membership[system_id==s & membership_grade=='system_member',plasmid_id]);outside<-setdiff(all_plasmids,members)
  if(length(members)<2 || length(outside)<2)next
  for(i in seq_len(nrow(terms<-unique(presence[,.(source,term)])))) {
    term<-terms$term[i];source<-terms$source[i];positive<-presence[presence$term==term & presence$source==source,plasmid_id]
    inside_n<-sum(members %in% positive);outside_n<-sum(outside %in% positive)
    if(inside_n+outside_n==0)next
    test<-fisher.test(matrix(c(inside_n,length(members)-inside_n,outside_n,length(outside)-outside_n),nrow=2,byrow=TRUE))
    result<-rbind(result,data.table(system_id=s,source=source,term=term,odds_ratio=unname(test$estimate),p_value=test$p.value,q_value=NA_real_))
  }
}
if(nrow(result))result[,q_value:=p.adjust(p_value,method='BH')]
fwrite(result,a[4],sep='\t')

# Family-coloured gene neighbourhoods are descriptive structure candidates,
# not nucleotide alignments or evidence of direct transfer.
dir.create(a[5])
genes<-fread(file.path(a[1],'genes.tsv'));families<-fread(file.path(a[1],'gene_family_clusters.tsv'))
features<-fread(file.path(a[3],'features.tsv'))
genes<-merge(genes,families[,.(gene_id,family_id)],by='gene_id',all.x=TRUE,sort=FALSE)
colours<-setNames(hcl.colors(length(unique(na.omit(genes$family_id))),palette='Dark 3'),sort(unique(na.omit(genes$family_id))))
plotted<-character()
for(s in unique(membership$system_id[nzchar(membership$system_id)])) {
  members<-sort(unique(membership[system_id==s & membership_grade=='system_member',plasmid_id]))
  members<-members[members %in% genes$plasmid_id]
  if(!length(members))next
  pdf(file.path(a[5],paste0(s,'.gene_order.pdf')),width=12,height=max(3,min(9,1.5+.35*length(members))))
  par(mar=c(4,18,4,2))
  pages<-split(members,ceiling(seq_along(members)/20))
  for(page in pages) {
    plot(NA,xlim=c(0,1),ylim=c(.5,length(page)+.5),xlab='Relative position in representative sequence',ylab='',yaxt='n',main=paste(s,'gene order; family colours; not an alignment'))
    axis(2,at=seq_along(page),labels=page,las=1,cex.axis=.45)
    for(i in seq_along(page)) {
      p<-page[i];n<-features[feature_id==p,length_bp]
      g<-genes[plasmid_id==p];start<-ifelse(g$strand=='-',g$end,g$start)/n;end<-ifelse(g$strand=='-',g$start,g$end)/n
      lines(c(0,1),c(i,i),col='grey70')
      colours_i<-unname(colours[g$family_id]);colours_i[is.na(colours_i)]<-'grey50'
      arrows(start,rep(i,nrow(g)),end,rep(i,nrow(g)),col=colours_i,length=.035,lwd=2)
    }
  }
  dev.off();plotted<-c(plotted,s)
}
write_json(list(status=if(length(plotted)) 'measured' else 'no_annotated_system_members',systems=as.list(plotted),
    policy='Shared gene families use shared colours; coordinates are relative to each sequence; adjacency differences remain candidates, not proven structural rearrangements'),
    file.path(a[5],'status.json'),pretty=TRUE,auto_unbox=TRUE)
