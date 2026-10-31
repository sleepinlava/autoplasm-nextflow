#!/usr/bin/env python3
"""Integrate native annotations on representative coordinates (1-based, inclusive)."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote
from protocol_catalogue import rows
from build_shared_catalogue import write_tsv,records,canonical


def gff_records(path):
    result=[]
    with path.open() as f:
        for line in f:
            if line.startswith('##FASTA'):break
            if line.startswith('#') or not line.strip():continue
            r=line.rstrip('\n').split('\t')
            attrs={k:unquote(v) for k,v in (a.split('=',1) for a in r[8].split(';') if '=' in a)}
            result.append(dict(plasmid_id=r[0],type=r[2],start=int(r[3]),end=int(r[4]),strand=r[6],gene_id=attrs.get('ID',''),product=attrs.get('product','')))
    return result


def native_table(path):
    with path.open() as f:
        lines=[]
        for line in f:
            if not line.strip():continue
            if line.startswith('#'):
                header=line.lstrip('# ').rstrip('\n')
                if header.split('\t')[0].split(',')[0] not in ('query','seqID','ID_integron'):continue
                line=header+'\n'
            lines.append(line)
    if not lines:return []
    lines[0]=lines[0].lstrip('#').lstrip()
    separator=',' if ',' in lines[0] and '\t' not in lines[0] else '\t'
    return list(csv.DictReader(lines,delimiter=separator))


def amr_evidence(method,subtype):
    if subtype=='POINT_DISRUPT' or 'INTERNAL_STOP' in method:return 'uncertain_function'
    if method.startswith(('ALLELE','EXACT')):return 'exact_reference_match'
    if method.startswith('PARTIAL'):return 'partial_match'
    if method.startswith('POINT'):return 'curated_point_mutation'
    if method.startswith('BLAST'):return 'homology_candidate'
    if method=='HMM':return 'family_candidate'
    return 'uncertain_match'


def integrate(catalogue,systems,genes,args,ises,integrons,mobility,eggnog,families,abundance,output,window,min_breadth=.75,min_depth=1.0):
    output.mkdir();lengths={r['feature_id']:int(r['length_bp']) for r in rows(catalogue/'features.tsv')}
    genes=[g for p in genes for g in gff_records(p) if g['type']=='CDS']
    gene_to_plasmid={g['gene_id']:g['plasmid_id'] for g in genes}
    write_tsv(output/'genes.tsv',['gene_id','plasmid_id','start','end','strand','product'],([g[k] for k in ['gene_id','plasmid_id','start','end','strand','product']] for g in genes))
    hits=[r for p in args for r in native_table(p)]
    raw_fields=list(dict.fromkeys(k for r in hits for k in r)) or ['Contig id','Element symbol','Type','Method']
    write_tsv(output/'amrfinder_hits.tsv',raw_fields,([r.get(k,'') for k in raw_fields] for r in hits))
    typed=[]
    for r in hits:
        method=r['Method'];subtype=r['Subtype']
        typed.append(dict(plasmid_id=r['Contig id'],start=int(r['Start']),end=int(r['Stop']),strand=r['Strand'],gene=r['Element symbol'],
            element_type=r['Type'],subtype=subtype,scope=r.get('Scope',''),method=method,
            subclass=r.get('Subclass',''),evidence_grade=amr_evidence(method,subtype)))
    typed_fields=['plasmid_id','gene','element_type','subtype','scope','method','evidence_grade','start','end','strand','subclass']
    write_tsv(output/'amrfinder_elements.tsv',typed_fields,([r[k] for k in typed_fields] for r in typed))
    annotations=[r for r in typed if r['element_type']=='AMR']
    elements=[]
    for folder in ises:
        for p in sorted(folder.rglob('*.csv')):
            for r in native_table(p):
                elements.append(dict(plasmid_id=r['seqID'],start=int(r['isBegin']),end=int(r['isEnd']),kind='IS',label=r['family']))
    for p in integrons:
        for r in native_table(p):
            elements.append(dict(plasmid_id=r['ID_replicon'],start=int(r['pos_beg']),end=int(r['pos_end']),kind='integron',label=r.get('type',r.get('annotation','integron'))))
    write_tsv(output/'mge.tsv',['plasmid_id','start','end','kind','label'],([r[k] for k in ['plasmid_id','start','end','kind','label']] for r in elements))
    context=[];modules=[];dna=dict(records(catalogue/'plasmids.fasta'))
    for a in annotations:
        fid=a['plasmid_id'];near=[]
        for e in elements:
            if fid!=e['plasmid_id']:continue
            distance=max(0,max(a['start'],e['start'])-min(a['end'],e['end'])-1)
            if distance<=window:near.append((distance,e))
        start=max(1,a['start']-window);end=min(lengths[fid],a['end']+window)
        truncated=start==1 or end==lengths[fid]
        labels=sorted({e['kind']+':'+e['label'] for _,e in near})
        context.append([fid,a['gene'],a['start'],a['end'],min((d for d,e in near),default=''), '|'.join(labels),int(truncated),'1-based inclusive'])
        # Sequence-defined local windows are candidates, not experimentally
        # demonstrated mobile units. Independent family clustering may link them.
        module='module_'+hashlib.sha256(canonical(dna[fid][start-1:end])[0].encode()).hexdigest()[:24]
        modules.append([module,fid,a['gene'],start,end,'|'.join(labels),int(truncated)])
    write_tsv(output/'ARG_context.tsv',['plasmid_id','arg','start','end','nearest_mge_distance_bp','nearby_mge','boundary_truncated','coordinate_system'],context)
    write_tsv(output/'mobile_module_candidates.tsv',['module_id','plasmid_id','arg','start','end','mge_signature','boundary_truncated'],modules)
    write_tsv(output/'args.tsv',['plasmid_id','arg','start','end','strand','subclass'],([r[k] for k in ['plasmid_id','gene','start','end','strand','subclass']] for r in annotations))
    known={r['plasmid_id']:r for r in rows(catalogue/'structure.tsv')}
    mobility_rows=[]
    for p in mobility:
        for r in native_table(p):
            fid=r['sample_id']
            grade={'conjugative':'conjugation_system_detected','mobilizable':'mobilization_features_detected'}.get(r['predicted_mobility'])
            if grade is None:grade='insufficient_fragment_evidence' if known[fid]['completeness']=='not_established' else 'no_detected_known_system'
            mobility_rows.append([fid,r['predicted_mobility'],r.get('rep_type(s)',''),r.get('relaxase_type(s)',''),r.get('mpf_type',''),r.get('orit_type(s)',''),known[fid]['completeness'],
                                  grade])
    write_tsv(output/'mobility.tsv',['plasmid_id','mobility','replicon','relaxase','mpf','orit','completeness','evidence_grade'],mobility_rows)
    membership=rows(systems/'membership.tsv');system_by_plasmid=defaultdict(set)
    for r in membership:
        if r['system_id']:system_by_plasmid[r['plasmid_id']].add(r['system_id'])
    family_rows=[]
    for p in families:
        with p.open() as f:
            for rep,gene in csv.reader(f,delimiter='\t'):family_rows.append([rep,gene,gene_to_plasmid[gene]])
    write_tsv(output/'gene_family_clusters.tsv',['family_id','gene_id','plasmid_id'],family_rows)
    presence=sorted({(p,f) for f,g,p in family_rows})
    write_tsv(output/'plasmid_gene_presence_absence.tsv',['plasmid_id','family_id','present'],([p,f,1] for p,f in presence))
    family_plasmids=defaultdict(set)
    for p,f in presence:family_plasmids[f].add(p)
    system_plasmids=defaultdict(set)
    for r in membership:
        if r['system_id'] and r['membership_grade']=='system_member':system_plasmids[r['system_id']].add(r['plasmid_id'])
    write_tsv(output/'system_gene_presence_absence.tsv',['system_id','family_id','positive_plasmids','total_plasmids','core'],
       ([s,f,len(ps&ms),len(ms),int(ms<=ps)] for s,ms in sorted(system_plasmids.items()) for f,ps in sorted(family_plasmids.items()) if ps&ms))
    functional=[]
    for p in eggnog:
        for r in native_table(p):
            gene=r['query'];fid=gene_to_plasmid[gene]
            for field in ['COG_category','KEGG_ko','KEGG_Pathway','GOs']:
                value=r.get(field,'-')
                for term in (list(value) if field=='COG_category' else value.split(',')):
                    if term and term!='-':functional.append([fid,gene,field,term])
    write_tsv(output/'functions.tsv',['plasmid_id','gene_id','source','term'],functional)
    by_plasmid=defaultdict(set)
    for a in annotations:by_plasmid[a['plasmid_id']].add(a['gene'])
    measured=rows(abundance);samples=sorted({r['sample_id'] for r in measured})
    detected_by_sample=defaultdict(set)
    counts=defaultdict(int)
    for r in measured:
        if float(r['breadth'])>=min_breadth and float(r['coverage'])>=min_depth:
            detected_by_sample[r['sample_id']].add(r['plasmid_id'])
            for arg in by_plasmid[r['plasmid_id']]:counts[r['sample_id'],arg]+=1
    for entities,label in [(system_plasmids,'system'),(detected_by_sample,'sample')]:
        summary=[]
        for entity,ps in sorted(entities.items()):
            terms=defaultdict(lambda: [set(),set()])
            for plasmid,gene,source,term in functional:
                if plasmid in ps:terms[source,term][0].add(plasmid);terms[source,term][1].add(gene)
            summary.extend([entity,source,term,len(plasmids),len(genes)] for (source,term),(plasmids,genes) in sorted(terms.items()))
        write_tsv(output/(label+'_function_summary.tsv'),[label+'_id','source','term','positive_plasmids','annotated_genes'],summary)
    all_args=sorted({a['gene'] for a in annotations})
    copies=defaultdict(int)
    for a in annotations:copies[a['plasmid_id'],a['gene']]+=1
    write_tsv(output/'plasmid_ARG_matrix.tsv',['plasmid_id','arg','gene_hits'],([p,a,copies[p,a]] for p in sorted(known) for a in all_args))
    write_tsv(output/'sample_ARG_matrix.tsv',['sample_id','arg','detected_plasmids'],([s,a,counts[s,a]] for s in samples for a in all_args))
    write_tsv(output/'system_ARG_matrix.tsv',['system_id','arg','positive_plasmids'],([s,a,sum(a in by_plasmid[p] for p in ps)] for s,ps in sorted(system_plasmids.items()) for a in all_args))
    gene_family={g:f for f,g,p in family_rows}
    gene_order=defaultdict(list)
    for g in genes:
        if g['gene_id'] in gene_family:gene_order[g['plasmid_id']].append(g)
    adjacency=[];edges=defaultdict(set)
    for plasmid,ordered in sorted(gene_order.items()):
        ordered.sort(key=lambda g:g['start'])
        for a,b in zip(ordered,ordered[1:]):
            fa,fb=gene_family[a['gene_id']],gene_family[b['gene_id']]
            flip={'+':'-','-':'+','.':'.'}
            edge=min((fa,a['strand'],fb,b['strand']),(fb,flip[b['strand']],fa,flip[a['strand']]))
            edges[plasmid].add(edge)
            adjacency.append([plasmid,fa,fb,a['strand'],b['strand'],b['start']-a['end']-1])
    write_tsv(output/'gene_order_adjacencies.tsv',['plasmid_id','family_a','family_b','strand_a','strand_b','intergenic_distance_bp'],adjacency)
    variants=[]
    for system,ps in sorted(system_plasmids.items()):
        if len(ps)<2:continue
        reference=sorted(ps)[0]
        for p in sorted(ps-{reference}):
            for edge in sorted(edges[p]^edges[reference]):variants.append([system,reference,p,*edge,'adjacency_difference_candidate','fragmentation_or_gene_calling_difference_remains_possible'])
    write_tsv(output/'system_structural_variants.tsv',['system_id','reference_plasmid','query_plasmid','family_a','strand_a','family_b','strand_b','interpretation','alternative_explanation'],variants)
    (output/'status.json').write_text(json.dumps(dict(coordinate_system='representative nucleotide sequence, 1-based inclusive',
       context_window_bp=window,module_policy='sequence-defined ARG windows; co-location does not establish mobility',
       amrfinder_status='measured' if args else 'not_assessed',amrfinder_plus_scope='AMR, STRESS and VIRULENCE from the configured reference database; not comprehensive virulence screening',
       missing_mechanism='absence in fragments is not evidence of biological nonmobilizability'),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['catalogue','systems','abundance','output']:p.add_argument('--'+k,type=Path,required=True)
 for k in ['genes','args','ises','integrons','mobility','eggnog','families']:p.add_argument('--'+k,nargs='*',type=Path,default=[])
 p.add_argument('--window',type=int,default=10000)
 p.add_argument('--min-breadth',type=float,default=.75);p.add_argument('--min-depth',type=float,default=1.0)
 integrate(**vars(p.parse_args()))
