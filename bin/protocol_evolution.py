#!/usr/bin/env python3
"""Build system-local single-copy core protein trees using MAFFT and IQ-TREE 2."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import subprocess
from protocol_catalogue import rows,fasta


def protein_records(path):
    name=None;pieces=[]
    with path.open() as f:
        for line in f:
            if line.startswith('>'):
                if name is not None:yield name,''.join(pieces)
                name=line[1:].split()[0];pieces=[]
            else:pieces.append(line.strip())
    if name is not None:yield name,''.join(pieces)


def evolve(annotations,systems,proteins,output,threads,min_members,min_core):
    output.mkdir();aa={gene:seq for p in proteins for gene,seq in protein_records(p)}
    gene_rows=rows(annotations/'genes.tsv');excluded=set()
    for g in gene_rows:
        if any(t in g['product'].lower() for t in ['transposase','integrase','recombinase']):excluded.add(g['gene_id'])
    # ARG neighborhoods are candidates for mobile cargo; they do not qualify
    # as conserved backbone markers just because they are shared.
    context=rows(annotations/'mobile_module_candidates.tsv')
    for g in gene_rows:
        if any(g['plasmid_id']==m['plasmid_id'] and int(g['start'])<=int(m['end']) and int(g['end'])>=int(m['start']) for m in context):excluded.add(g['gene_id'])
    family=defaultdict(lambda:defaultdict(list))
    for r in rows(annotations/'gene_family_clusters.tsv'):
        if r['gene_id'] not in excluded:family[r['family_id']][r['plasmid_id']].append(r['gene_id'])
    members=defaultdict(set)
    for r in rows(systems/'membership.tsv'):
        if r['eligible_for_abundance']=='1':members[r['system_id']].add(r['plasmid_id'])
    statuses=[];trees=[]
    for system,ps in sorted(members.items()):
        core={f:v for f,v in family.items() if all(len(v.get(p,[]))==1 for p in ps) and all(len(aa[v[p][0]])>=50 for p in ps)}
        entry=dict(system_id=system,plasmids=sorted(ps),core_genes=len(core),status='ineligible')
        if len(ps)<min_members or len(core)<min_core:
            entry['reason']='insufficient_comparable_nonmobile_single_copy_core';statuses.append(entry);continue
        folder=output/system;folder.mkdir();concat={p:'' for p in sorted(ps)};partition=[];offset=1
        for index,(family_id,g) in enumerate(sorted(core.items()),1):
            query=folder/f'core_{index}.faa';aligned=folder/f'core_{index}.aligned.faa'
            fasta(query,((p,aa[g[p][0]]) for p in sorted(ps)))
            with aligned.open('w') as stdout:subprocess.run(['mafft','--auto','--thread',str(threads),str(query)],stdout=stdout,check=True)
            aligned_records=dict(protein_records(aligned));n=len(next(iter(aligned_records.values())))
            if set(aligned_records)!=ps or len({len(v) for v in aligned_records.values()})!=1:raise ValueError('MAFFT changed taxa or returned unequal aligned lengths')
            for p in ps:concat[p]+=aligned_records[p]
            partition.append(f'LG, core_{index} = {offset}-{offset+n-1}');offset+=n
        alignment=folder/'backbone_alignments.fasta';fasta(alignment,concat.items())
        (folder/'partitions.raxml').write_text('\n'.join(partition)+'\n')
        subprocess.run(['iqtree2','-s',str(alignment),'-m','MFP','-B','1000','-alrt','1000','-seed','20261030','-T',str(threads),'--prefix',str(folder/'backbone')],check=True)
        trees.append((folder/'backbone.treefile').read_text().strip());entry['status']='measured';entry['reason']='';statuses.append(entry)
    (output/'system_phylogenies.nwk').write_text('\n'.join(trees)+'\n' if trees else '')
    (output/'status.json').write_text(json.dumps(dict(systems=statuses,policy='system-local core proteins only; exclusion of annotated mobile cargo does not prove absence of recombination; trees are not transmission trees'),indent=2)+'\n')
    with (output/'versions.txt').open('w') as f:
        for cmd in [['mafft','--version'],['iqtree2','-version']]:subprocess.run(cmd,stdout=f,stderr=f,check=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['annotations','systems','output']:p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--proteins',type=Path,nargs='*',default=[]);p.add_argument('--threads',type=int,default=1);p.add_argument('--min-members',type=int,default=4);p.add_argument('--min-core',type=int,default=3)
 evolve(**vars(p.parse_args()))
