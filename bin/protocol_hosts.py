#!/usr/bin/env python3
"""Coordinate-consistent MAG measurements and explicitly graded host evidence."""
import argparse
from collections import defaultdict
import csv
import hashlib
import itertools
import json
from pathlib import Path
from protocol_catalogue import rows
from build_shared_catalogue import records,write_tsv


def intervals_length(intervals):
    end=0;total=0
    for a,b in sorted((min(a,b),max(a,b)) for a,b in intervals):
        total+=max(0,b-max(end,a-1));end=max(end,b)
    return total


def plsdb(alignments,hosts,output,identity,coverage):
    labels={r['reference_id']:r['host_taxonomy'] for r in rows(hosts)}
    hits=defaultdict(list)
    with alignments.open() as f:
        for r in csv.reader(f,delimiter='\t'):
            if float(r[2])/100>=identity:hits[r[0],r[1]].append(r)
    result=[]
    for (query,reference),blocks in sorted(hits.items()):
        qcov=intervals_length([(int(r[4]),int(r[5])) for r in blocks])/int(blocks[0][8])
        scov=intervals_length([(int(r[6]),int(r[7])) for r in blocks])/int(blocks[0][9])
        if min(qcov,scov)>=coverage:
            result.append([query,reference,labels[reference],qcov,scov,min(float(r[2]) for r in blocks)/100,'reference_homology'])
    write_tsv(output,['plasmid_id','reference_id','host_taxonomy','query_coverage','reference_coverage','min_identity','evidence_grade'],result)


def mags(spec,catalogue,abundance,output,min_completeness,max_contamination,min_locus_fraction=.75):
    """Assign eligible reference contigs to exact bin entities; shared loci stay ambiguous."""
    output.mkdir();spec=json.loads(spec.read_text())
    source={(r['sample_id'],r['contig_id']):r['feature_id'] for r in rows(catalogue/'sources.tsv')}
    feature_rows=rows(catalogue/'features.tsv')
    lengths={r['feature_id']:int(r['length_bp']) for r in feature_rows}
    plasmid_features={r['feature_id'] for r in feature_rows if r['is_plasmid']=='1'}
    bins={};origin=[]
    for item in spec:
        quality={r['Name']:r for r in rows(Path(item['quality']))}
        taxonomy={r['user_genome']:r['classification'] for path in item['taxonomy'] for r in rows(Path(path))}
        for path in map(Path,item['bins']):
            q=quality[path.stem];complete=float(q['Completeness']);contamin=float(q['Contamination'])
            members=sorted({source[item['sample_id'],cid] for cid,dna in records(path)})
            eligible=complete>=min_completeness and contamin<=max_contamination
            mag='mag_'+hashlib.sha256('\n'.join(members).encode()).hexdigest()[:24]
            origin.append([item['sample_id'],path.stem,mag,complete,contamin,int(eligible),taxonomy.get(path.stem,'unknown')])
            if eligible:bins[mag]=members
    write_tsv(output/'quality.tsv',['sample_id','bin_id','mag_id','completeness','contamination','eligible','taxonomy'],origin)
    write_tsv(output/'MAG_quality_flags.tsv',['sample_id','bin_id','mag_id','mimag_quality','high_quality_completeness_contamination_candidate','rna_requirement_status'],
        ([sample,bin_id,mag,'medium_quality' if complete>=50 and contamin<10 else 'low_quality',int(complete>90 and contamin<5),'not_assessed_no_high_quality_certification']
         for sample,bin_id,mag,complete,contamin,eligible,taxonomy in origin))
    owners=defaultdict(set)
    for mag,members in bins.items():
        for fid in members:owners[fid].add(mag)
    unique={fid:next(iter(ms)) for fid,ms in owners.items() if len(ms)==1 and fid not in plasmid_features}
    total_lengths={mag:sum(lengths[fid] for fid in members) for mag,members in bins.items()}
    unique_lengths={mag:sum(lengths[fid] for fid in members if unique.get(fid)==mag) for mag,members in bins.items()}
    write_tsv(output/'strain_eligible_mags.tsv',['mag_id','unique_locus_fraction'],([mag,unique_lengths[mag]/total_lengths[mag]] for mag in sorted(bins) if unique_lengths[mag]/total_lengths[mag]>=min_locus_fraction))
    write_tsv(output/'scaffold_to_bin.tsv',['contig_id','mag_id'],sorted(unique.items()))
    measured=rows(abundance);samples=sorted({r['sample_id'] for r in measured})
    values=defaultdict(lambda:defaultdict(float))
    for r in measured:
        fid=r['contig_id']
        if fid not in unique:continue
        key=(unique[fid],r['sample_id']);n=lengths[fid]
        for field in ['coverage','breadth']:values[key][field]+=float(r[field])*n
        values[key]['raw_count']+=int(r['raw_count'])
    write_tsv(output/'mag_abundance.tsv',['mag_id','sample_id','coverage','breadth','raw_count','eligible_length_bp','count_unit','mag_length_bp','unique_locus_fraction'],
        ([mag,sample,values[mag,sample]['coverage']/length,values[mag,sample]['breadth']/length,int(values[mag,sample]['raw_count']),length,'proper_paired_fragment',total_lengths[mag],unique_lengths[mag]/total_lengths[mag]]
         for mag in sorted(bins) if (length:=sum(lengths[fid] for fid in bins[mag] if unique.get(fid)==mag))>0 for sample in samples))
    (output/'status.json').write_text(json.dumps(dict(status='measured' if bins else 'no_qualified_mags',
        minimum_completeness=min_completeness,maximum_contamination=max_contamination,
        ambiguous_loci_excluded=sum(len(v)>1 for v in owners.values()),
        taxonomy_policy='GTDB labels; low-contamination/high-completeness alone does not establish MIMAG high quality'),indent=2)+'\n')


def host_matrix(plasmids,mags,metadata,output,strata,subject,min_samples,prevalence):
    output.mkdir();md=rows(metadata);ab=rows(plasmids);mag=rows(mags/'mag_abundance.tsv')
    cols=[s for s in strata.split(',') if s];cohorts=defaultdict(list)
    fields=set(md[0])
    if set(cols+([subject] if subject else []))-fields:raise ValueError('Missing host association metadata columns')
    for r in md:
        if any(r[k] in ('','NA') for k in cols+([subject] if subject else [])):raise ValueError('Missing host confounder metadata')
        cohorts[tuple(r[k] for k in cols)].append(r)
    values=defaultdict(dict)
    for data,feature,prefix in [(ab,'plasmid_id','P:'),(mag,'mag_id','M:')]:
        for r in data:values[prefix+r[feature]][r['sample_id']]=int(r['raw_count'])
    status=[]
    for key,samples in sorted(cohorts.items()):
        samples=sorted(samples,key=lambda r:r['sample_id'])
        if subject:
            # One observation per subject within a stratum: FastSpar has no
            # repeated-measures model. The deterministic retained rows are recorded.
            selected={}
            for r in samples:selected.setdefault(r[subject],r)
            samples=list(selected.values())
        ids=[r['sample_id'] for r in samples]
        excluded_empty=[s for s in ids if not any(v.get(s,0)>0 for v in values.values())]
        ids=[s for s in ids if s not in excluded_empty]
        if not ids:
            status.append(dict(stratum_id='',values=list(key),sample_ids=[],excluded_empty=excluded_empty,eligible=False,features=0,reason='all_samples_empty'))
            continue
        retained={fid:[v[s] for s in ids] for fid,v in values.items()
                  if all(s in v for s in ids) and sum(v[s]>0 for s in ids)/len(ids)>=prevalence and len({v[s] for s in ids})>1}
        ok=len(ids)>=min_samples and len(retained)>=3 and any(x.startswith('P:') for x in retained) and any(x.startswith('M:') for x in retained)
        name='stratum_'+hashlib.sha256(json.dumps(key).encode()).hexdigest()[:12]
        if ok:write_tsv(output/(name+'.tsv'),['#OTU ID']+ids,([fid]+retained[fid] for fid in sorted(retained)))
        status.append(dict(stratum_id=name,values=list(key),sample_ids=ids,excluded_empty=excluded_empty,eligible=ok,features=len(retained),reason='' if ok else 'insufficient_independent_samples_or_features'))
    (output/'status.json').write_text(json.dumps(dict(strata=cols,subject=subject,cohorts=status,
        control='categorical stratification; one sample per subject per stratum; associations are not physical host assignments'),indent=2)+'\n')


def host_edges(correlation,pvalues,output,stratum,min_correlation,max_q):
    with correlation.open() as f:
        reader=csv.reader(f,delimiter='\t');header=next(reader)[1:];cor={r[0]:dict(zip(header,map(float,r[1:]))) for r in reader}
    with pvalues.open() as f:
        reader=csv.reader(f,delimiter='\t');header=next(reader)[1:];pv={r[0]:dict(zip(header,map(float,r[1:]))) for r in reader}
    tests=[(p,m,pv[p][m],cor[p][m]) for p in sorted(cor) if p.startswith('P:') for m in sorted(cor) if m.startswith('M:')]
    ranked=sorted(enumerate(tests),key=lambda x:x[1][2]);adjusted={};last=1
    for rank,(idx,test) in reversed(list(enumerate(ranked,1))):last=min(last,test[2]*len(tests)/rank);adjusted[idx]=last
    write_tsv(output,['plasmid_id','mag_id','stratum_id','correlation','p_value','q_value','evidence_grade'],
      ([p[2:],m[2:],stratum,c,pv,adjusted[i],'coabundance_association'] for i,(p,m,pv,c) in enumerate(tests) if c>=min_correlation and adjusted[i]<=max_q))


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 q=sub.add_parser('plsdb')
 for k in ['alignments','hosts','output']:q.add_argument('--'+k,type=Path,required=True)
 for k in ['identity','coverage']:q.add_argument('--'+k,type=float,required=True)
 q=sub.add_parser('mags')
 for k in ['spec','catalogue','abundance','output']:q.add_argument('--'+k,type=Path,required=True)
 for k in ['min-completeness','max-contamination']:q.add_argument('--'+k,type=float,required=True)
 q.add_argument('--min-locus-fraction',type=float,default=.75)
 q=sub.add_parser('host_matrix')
 for k in ['plasmids','mags','metadata','output']:q.add_argument('--'+k,type=Path,required=True)
 q.add_argument('--strata',default='group');q.add_argument('--subject',default='');q.add_argument('--min-samples',type=int,default=20);q.add_argument('--prevalence',type=float,default=.1)
 q=sub.add_parser('host_edges')
 for k in ['correlation','pvalues','output']:q.add_argument('--'+k,type=Path,required=True)
 q.add_argument('--stratum',required=True);q.add_argument('--min-correlation',type=float,default=.6);q.add_argument('--max-q',type=float,default=.05)
 a=vars(p.parse_args());fn=a.pop('command');globals()[fn](**a)
