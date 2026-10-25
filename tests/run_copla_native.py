#!/usr/bin/env python3
"""Run the production COPLA node on fixed complete official independent plasmids."""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
EXPECTED={'NZ_CP028167.1':'PTU-X4','NZ_CP028329.1':'PTU-Lab26'}


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['work-dir','assembly','installation','refgraph','reflist','macsyfinder','prefix']:
        p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--sample-id',default='two_plasmids')
    a=p.parse_args();base=a.work_dir.resolve();base.mkdir(parents=True,exist_ok=False)
    source_files=['modules/typing/copla.nf','bin/run_copla_candidates.py','tests/nextflow/copla_native.nf','tests/run_copla_native.py','envs/copla.yml']
    sources={n:sha(ROOT/n) for n in source_files};assembly=a.assembly.resolve();input_sha=sha(assembly)
    params={n:str(getattr(a,n).resolve()) for n in ['assembly','installation','refgraph','reflist','macsyfinder']}
    params.update(sample_id=a.sample_id,outdir=str(base/'out'))
    (base/'params.json').write_text(json.dumps(params))
    config=base/'config'
    config.write_text("process.executor='local'\nprocess.cpus=2\nprocess.memory='6 GB'\nconda.enabled=false\n"
                      "docker.enabled=false\nsingularity.enabled=false\npodman.enabled=false\nparams.publish_dir_mode='copy'\n"
                      "trace.fields='task_id,hash,name,status,exit,workdir'\n")
    command=[shutil.which('nextflow') or 'nextflow','-C',str(config),'run',str(ROOT/'tests/nextflow/copla_native.nf'),
             '-params-file',str(base/'params.json'),'-work-dir',str(base/'work'),'-with-trace',str(base/'trace.tsv'),'-ansi-log','false']
    result=subprocess.run(command,cwd=base,env={**os.environ,'PATH':str(a.prefix.resolve()/'bin')+os.pathsep+os.environ['PATH']},capture_output=True,text=True)
    (base/'console.log').write_text(result.stdout+result.stderr)
    with (base/'trace.tsv').open() as f:tasks=list(csv.DictReader(f,delimiter='\t'))
    assert result.returncode==0 and len(tasks)==1 and tasks[0]['status']=='COMPLETED',result.stdout+result.stderr
    work=Path(tasks[0]['workdir']);out=base/'out/06_plasmid_typing/copla';raw=out/(a.sample_id+'.copla')
    with (out/(a.sample_id+'.copla.tsv')).open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
    manifest=json.loads((raw/'entities.json').read_text())
    assert manifest['source_patch']['applied'] and manifest['reference_count']==9894
    assert manifest['runtime_versions']['graph_tool'].startswith('2.35')
    # Independent parser; neither the producer adapter nor its FASTA reader is reused.
    script=('from Bio import SeqIO\nimport gzip,json,sys,hashlib\n'
            'f=gzip.open(sys.argv[1],"rt") if sys.argv[1].lower().endswith(".gz") else open(sys.argv[1])\n'
            'd=SeqIO.to_dict(SeqIO.parse(f,"fasta"));f.close()\n'
            'print(json.dumps({k:{"length":len(v.seq),"DNA_sha256":hashlib.sha256(str(v.seq).encode()).hexdigest()} for k,v in d.items()}))\n')
    independent=subprocess.run([str(a.prefix.resolve()/'bin/python3'),'-c',script,str(assembly)],capture_output=True,text=True)
    assert independent.returncode==0,independent.stderr
    truth=json.loads(independent.stdout)
    assert set(truth)<=set(EXPECTED) and len(rows)==len(truth)==len(manifest['entities'])
    assert {r['contig_id'] for r in rows}==set(truth)
    assert {r['id'] for r in manifest['entities']}==set(truth)
    for row in rows:
        sid=row['contig_id'];assert row['predicted_ptu']==EXPECTED[sid]
        assert float(row['score'])>=0.9 and int(row['length'])==truth[sid]['length']
        entity=next(e for e in manifest['entities'] if e['id']==sid)
        assert entity['DNA_sha256']==truth[sid]['DNA_sha256']
        assert row['entity_scope']=='candidate_record' and row['topology']=='linear'
    assert not (raw/'databases').exists() and not (raw/'reference.pickle').exists()
    assert (work/'run_copla_candidates.py').read_bytes()==(ROOT/'bin/run_copla_candidates.py').read_bytes()
    assert sha(assembly)==input_sha and all(sha(ROOT/n)==h for n,h in sources.items())
    (base/'run.json').write_text(json.dumps({'pass':True,'command':command,'tasks':tasks,'source_sha256':sources,
         'assembly_sha256':input_sha,'independent_BioPython':truth,'rows':rows,'manifest':manifest,
         'expected_PTUs':EXPECTED,'expected_source':'Fixed official COPLA test/*.tgz predictions; score>=0.9 per official confidence recommendation',
         'limitations':['Two official examples, not population sensitivity/specificity or full platform/profile certification',
                        'No host taxonomy supplied: host-range is not compared to taxonomically annotated official demonstration',
                        'Complete archive/source/runtime identities are in the separate preparation receipts']},indent=2)+'\n')
    print('PASS complete COPLA model and9894 references, independently attributed candidates',len(rows),flush=True)


if __name__=='__main__':main()
