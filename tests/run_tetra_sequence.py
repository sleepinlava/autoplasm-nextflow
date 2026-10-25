#!/usr/bin/env python3
"""Native R/original LINK_SEQUENCE on locked DNA with explicit self/fragment controls.

MAG files here are controlled input fixtures, not known plasmid-host assignments.
No threshold is calibrated from these positive/negative mathematical controls.
"""
import argparse
import csv
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
from test_tetra_math import zscores, pearson, rc

ROOT=Path(__file__).resolve().parents[1]


def fasta(path):
    records=[];name=None;dna=[]
    for line in path.read_text().splitlines():
        if line.startswith('>'):
            if name is not None: records.append((name,''.join(dna)))
            name=line[1:].split()[0];dna=[]
        else:dna.append(line.strip())
    if name is not None:records.append((name,''.join(dna)))
    return records


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work-dir',type=Path,required=True);p.add_argument('--references',type=Path,required=True);p.add_argument('--before-dir',type=Path,required=True);args=p.parse_args();base=args.work_dir.resolve();base.mkdir(parents=True,exist_ok=False)
    fixture=base/'fixtures';fixture.mkdir();lock=json.loads((ROOT/'tests/structure-reference.lock.json').read_text())
    dna=[]
    for accession in ['NC_007941.1','NC_003903.1']:
        item=next(x for x in lock['references'] if x['accession']==accession);ref=next(q for q in args.references.glob('*.fasta') if q.name.startswith(accession));assert hashlib.sha256(ref.read_bytes()).hexdigest()==item['files']['fasta'];dna.append(fasta(ref)[0][1])
    expected={}
    for sid,seq,other in [('P',dna[0],dna[1]),('S',dna[1],dna[0])]:
        d=fixture/sid;mag=d/'MAG files';mag.mkdir(parents=True)
        plasmids=[('self_control',seq),('unrelated_control',other),('homopolymer','A'*1200),('periodic','ACGT'*300),('too_short',seq[:999])]
        (d/'plasmids.fasta').write_text(''.join('>'+n+'\n'+s+'\n' for n,s in plasmids))
        sequences={'full':[seq],'fragmented':[seq[i:i+997] for i in range(0,len(seq),997)],'reverse':[rc(seq)]}
        for name,records in sequences.items():
            text=''.join(f'>contig{i}\n{s}\n' for i,s in enumerate(records))
            if name=='reverse':
                with gzip.open(mag/(name+'.fa.gz'),'wt') as f:f.write(text)
            else:(mag/(name+'.fa')).write_text(text)
        (d/'taxonomy.tsv').write_text('user_genome\tclassification\n'+'\n'.join(n+'.fa\td__Controlled_input' for n in ['full','fragmented'])+'\n')
        (d/'second-domain').mkdir()
        (d/'second-domain/taxonomy.tsv').write_text('user_genome\tclassification\nreverse.fa.gz\td__Controlled_input\n')
        expected[sid]={}
        for pid,pseq in plasmids:
            if len(pseq)<1000:continue
            for host,records in sequences.items():expected[sid][pid+'|'+host]=pearson(zscores([pseq]),zscores(records))
    source_names=['bin/sequence_similarity_link.R','modules/linking/sequence.nf','tests/run_tetra_sequence.py','tests/nextflow/tetra_sequence.nf','tests/test_tetra_math.py']
    source_sha={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in source_names};hashes={str(q.relative_to(fixture)):hashlib.sha256(q.read_bytes()).hexdigest() for q in fixture.rglob('*') if q.is_file()}
    (base/'inputs-before.json').write_text(json.dumps(hashes,indent=2)+'\n')
    config=base/'native.config';config.write_text(f"params.outdir='{base}/out'\nparams.fixture_dir='{fixture}'\nparams.publish_dir_mode='copy'\nparams.link_min_similarity=0.7\nprocess.executor='local'\nprocess.cpus=1\nprocess.memory='1 GB'\nprocess.maxForks=1\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\ntrace.fields='task_id,hash,name,status,exit,workdir'\n")
    cmd=[shutil.which('nextflow') or 'nextflow','-C',str(config),'run',str(ROOT/'tests/nextflow/tetra_sequence.nf'),'-work-dir',str(base/'work'),'-with-trace',str(base/'trace.tsv'),'-ansi-log','false'];env=os.environ.copy();env['PATH']=str(ROOT/'bin')+':'+env['PATH'];r=subprocess.run(cmd,env=env,text=True,capture_output=True);(base/'console.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stdout+r.stderr
    tasks=list(csv.DictReader((base/'trace.tsv').open(),delimiter='\t'));assert len(tasks)==2 and all(t['status']=='COMPLETED' and t['exit']=='0' for t in tasks)
    observed={}
    for sid in expected:
        out=base/'out/07_host_prediction/linking/sequence';scores=list(csv.DictReader((out/(sid+'.sequence_scores.tsv')).open(),delimiter='\t'));assert len(scores)==12
        actual={row['plasmid_id']+'|'+row['host_id']:row for row in scores};assert actual.keys()==expected[sid].keys()
        for key,value in expected[sid].items():
            row=actual[key];assert row['sample_id']==sid and row['method']=='tetra_markov256_v1' and row['threshold_status']=='not_applied_uncalibrated' and row['association_status']=='disabled_uncalibrated' and row['host_taxonomy']=='d__Controlled_input'
            if value is None:assert row['score']=='' and row['profile_status']=='ineligible_profile' and 'threshold_pass' not in row
            else:assert math.isclose(float(row['score']),value,rel_tol=1e-10,abs_tol=1e-10),(sid,key,row['score'],value)
        links=list(csv.DictReader((out/(sid+'.sequence_links.tsv')).open(),delimiter='\t'));assert not links, 'Uncalibrated scores must never emit host associations'
        assert all('threshold_pass' not in row for row in scores)
        info=json.loads((out/(sid+'.sequence_method.json')).read_text());assert info['dimensions']==256 and info['method']=='tetra_markov256_v1' and info['threshold_status']=='not_applied_uncalibrated' and info['host_links_enabled'] is False;assert info['short_plasmids']=='too_short';assert info['mag_profiles']=={h:'complete256' for h in ['full','fragmented','reverse']};assert info['plasmid_profiles']['homopolymer']=='undefined_markov_variance';observed[sid]=scores
    # Actual legacy-folded numeric counterexample. This only reads frozen script definitions.
    old=base/'legacy-probe.R';old.write_text('''args <- commandArgs(TRUE); e<-parse(args[1]); for(x in e[-length(e)])eval(x)
a<-read_fasta(args[2])[[1]]$seq;b<-read_fasta(args[3])[[1]]$seq
cat(sprintf("%.17g\\n",similarity(tetra_zscores(a),tetra_zscores(b))))
''')
    rng=random.Random(20261020);a=''.join(rng.choices('ACGT',weights=[.35,.15,.2,.3],k=4000));bb=''.join(rng.choice('ACGT') if rng.random()<.18 else x for x in a)
    for name,s in [('a',a),('b',bb)]:(base/(name+'.fa')).write_text('>'+name+'\n'+s+'\n')
    oldcmd=['Rscript',str(old),str(args.before_dir.resolve()/'bin/sequence_similarity_link.R'),str(base/'a.fa'),str(base/'b.fa')];before=subprocess.run(oldcmd,text=True,capture_output=True,check=True);oldscore=float(before.stdout);newscore=pearson(zscores([a]),zscores([bb]));assert oldscore>.7 and newscore<.7
    # Current public CLI produces the lower independent score (not only the helper probe).
    cmag=base/'counter-MAG';cmag.mkdir();(cmag/'candidate.fa').write_text('>candidate\n'+bb+'\n')
    ccmd=['Rscript',str(ROOT/'bin/sequence_similarity_link.R'),'--plasmid-contigs',str(base/'a.fa'),'--host-genomes',str(cmag),'--out',str(base/'counter.links.tsv'),'--out-scores',str(base/'counter.scores.tsv'),'--min-similarity','0.7'];cr=subprocess.run(ccmd,text=True,capture_output=True,check=True);crow=list(csv.DictReader((base/'counter.scores.tsv').open(),delimiter='\t'));assert len(crow)==1 and math.isclose(float(crow[0]['score']),newscore,abs_tol=1e-10);assert not list(csv.DictReader((base/'counter.links.tsv').open(),delimiter='\t'))
    assert source_sha=={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in source_names};assert hashes=={str(q.relative_to(fixture)):hashlib.sha256(q.read_bytes()).hexdigest() for q in fixture.rglob('*') if q.is_file()}
    record={'pass':True,'command':cmd,'exit':r.returncode,'tasks':tasks,'source_sha256':source_sha,'fixture_sha256':hashes,'expected':expected,'observed':observed,'legacy_counterexample':{'command':oldcmd,'score':oldscore,'current_expected':newscore,'current_cli_command':ccmd,'threshold':.7,'legacy_passes_current_rejects':True},'limitations':['locked real DNA with explicit self/fragment/unrelated controls and independent scalar math, not known biological plasmid-host associations','not host accuracy or threshold calibration; uncalibrated host links are disabled','native local R/Biostrings/Nextflow; no image/nf-test framework/full platform claim']};(base/'run.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n');print('PASS2 native LINK_SEQUENCE tasks;24 independent pair scores; legacy threshold crossing',oldscore,newscore)


if __name__=='__main__':main()
