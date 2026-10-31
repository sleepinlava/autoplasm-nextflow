#!/usr/bin/env python3
"""Normalize native MobMess systems without turning fragments into complete plasmids."""
import argparse
import hashlib
import json
from pathlib import Path
from collections import defaultdict
from protocol_catalogue import rows
from build_shared_catalogue import write_tsv


def normalize(native, catalogue, output):
    output.mkdir(exist_ok=True)
    systems=rows(native/'mobmess_systems.txt') if (native/'mobmess_systems.txt').exists() else []
    names={r['system_name']:'system_'+hashlib.sha256(r['backbone_plasmids'].encode()).hexdigest()[:20] for r in systems}
    write_tsv(output/'systems.tsv',['system_id','native_system_id','backbone_plasmids','compound_plasmids'],
        ([names[r['system_name']],r['system_name'],r['backbone_plasmids'],r['compound_plasmids']] for r in systems))
    contigs=rows(native/'mobmess_contigs.txt') if systems else []
    supported={r['plasmid_id'] for r in rows(catalogue/'structure.tsv') if r['completeness'] in ('independently_supported','predicted_near_complete')}
    membership=[];observed=set()
    for r in contigs:
        cid=r['contig'];observed.add(cid)
        targets=[s for s in r['systems'].split('|') if s]
        for system in targets:
            membership.append([cid,names[system],r['cluster_type'],
                'fragment_linked' if r['cluster_type']=='fragment' or cid not in supported else 'system_member',
                int(len(targets)==1 and r['cluster_type']!='fragment' and cid in supported)])
        if not targets:membership.append([cid,'',r['cluster_type'],'unassigned',0])
    for r in rows(catalogue/'structure.tsv'):
        if r['plasmid_id'] not in observed:membership.append([r['plasmid_id'],'','unknown','unassigned',0])
    write_tsv(output/'membership.tsv',['plasmid_id','system_id','cluster_type','membership_grade','eligible_for_abundance'],membership)
    (output/'status.json').write_text(json.dumps(dict(status='measured' if systems else 'no_systems',
        systems=len(systems),completeness_policy='independent support or high-confidence graph-derived single-contig bin plus circularity; predicted candidates are not confirmed closed molecules',
        abundance_policy='only unambiguous nonfragment members; fragment-linked and multi-system members excluded'),indent=2)+'\n')


def aggregate(abundance, systems, output):
    membership=rows(systems/'membership.tsv');data=rows(abundance)
    eligible={r['plasmid_id']:r['system_id'] for r in membership if r['eligible_for_abundance']=='1'}
    samples=sorted({r['sample_id'] for r in data});ids=sorted({r['system_id'] for r in membership if r['system_id']})
    values=defaultdict(lambda:defaultdict(float))
    for r in data:
        if r['plasmid_id'] in eligible:
            key=(eligible[r['plasmid_id']],r['sample_id'])
            for metric in ['coverage','raw_count','tpm','rpkm']:values[key][metric]+=float(r[metric])
    write_tsv(output,['plasmid_id','sample_id','coverage','raw_count','tpm','rpkm','count_unit','entity_level'],
        ([system,sample,values[system,sample]['coverage'],int(values[system,sample]['raw_count']),values[system,sample]['tpm'],values[system,sample]['rpkm'],'proper_paired_fragment','system'] for system in ids for sample in samples))


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);q=p.add_subparsers(dest='command',required=True)
 n=q.add_parser('normalize');n.add_argument('--native',type=Path,required=True);n.add_argument('--catalogue',type=Path,required=True);n.add_argument('--output',type=Path,required=True)
 n=q.add_parser('aggregate');n.add_argument('--abundance',type=Path,required=True);n.add_argument('--systems',type=Path,required=True);n.add_argument('--output',type=Path,required=True)
 a=vars(p.parse_args());fn=a.pop('command');globals()[fn](**a)
