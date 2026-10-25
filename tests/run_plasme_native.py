#!/usr/bin/env python3
"""Run the real configured PLASMe source through its original production node."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:
        result=hashlib.sha256()
        for chunk in iter(lambda:stream.read(1024*1024),b''):result.update(chunk)
        return result.hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work-dir',type=Path,required=True)
    p.add_argument('--source-dir',type=Path,required=True)
    p.add_argument('--database',type=Path,required=True)
    p.add_argument('--assembly',type=Path,required=True)
    p.add_argument('--python',type=Path,required=True)
    p.add_argument('--backend',choices=['native','conda','podman'],default='native')
    p.add_argument('--conda-cache',type=Path)
    p.add_argument('--expect',choices=['positive','no-hit'],required=True)
    p.add_argument('--sample-id',default='plasmid')
    p.add_argument('--require-transformer',action='store_true')
    a=p.parse_args();base=a.work_dir.resolve();base.mkdir(parents=True,exist_ok=False)
    source,db,assembly,python=map(lambda q:q.resolve(),[a.source_dir,a.database,a.assembly,a.python])
    production=['modules/detection/plasme.nf','bin/plasme_runtime.py','bin/normalize_plasme_outputs.py',
                'envs/plasme.yml','tests/nextflow/plasme_native.nf','tests/run_plasme_native.py']
    sources={str(ROOT/n):sha(ROOT/n) for n in production}
    sources.update({str(source/n):sha(source/n) for n in ['PLASMe.py','bio_script.py','trans_data.py','trans_model.py']})
    before=sha(assembly)
    config=base/'native.config'
    text="process.executor='local'\nprocess.cpus=1\nprocess.memory='6 GB'\ntrace.fields='task_id,hash,name,status,exit,workdir'\n"
    text+="params.publish_dir_mode='copy'\nparams.plasme_container=null\ndocker.enabled=false\nsingularity.enabled=false\n"
    text+='podman.enabled='+str(a.backend=='podman').lower()+'\nconda.enabled='+str(a.backend=='conda').lower()+'\n'
    if a.backend=='conda':
        cache=(a.conda_cache or base/'conda-cache').resolve()
        text+='conda.useMicromamba=true\nconda.cacheDir='+repr(str(cache))+'\n'
    config.write_text(text)
    params={'outdir':str(base/'out'),'source_dir':str(source),'database':str(db),'assembly':str(assembly),'sample_id':a.sample_id}
    pf=base/'params.json';pf.write_text(json.dumps(params))
    command=[shutil.which('nextflow') or 'nextflow','-C',str(config),'run',str(ROOT/'tests/nextflow/plasme_native.nf'),
             '-params-file',str(pf),'-work-dir',str(base/'work'),'-with-trace',str(base/'trace.tsv'),'-ansi-log','false']
    env={**os.environ,'PATH':str(python.parent)+os.pathsep+os.environ['PATH']}
    result=subprocess.run(command,cwd=base,env=env,capture_output=True,text=True)
    (base/'console.log').write_text(result.stdout+result.stderr)
    with (base/'trace.tsv').open() as stream:tasks=list(csv.DictReader(stream,delimiter='\t'))
    assert result.returncode==0 and len(tasks)==1 and tasks[0]['status']=='COMPLETED',result.stdout+result.stderr
    work=Path(tasks[0]['workdir']);out=base/'out/04_plasmid_detection/plasme'
    runtime=json.loads((out/(a.sample_id+'.plasme_runtime.json')).read_text())
    assert runtime['local_source_patch']['applied'] and runtime['exit_code']==0
    assert runtime['versions']['torch']=='1.11.0'
    with (out/(a.sample_id+'.plasme.tsv')).open() as stream:rows=list(csv.DictReader(stream,delimiter='\t'))
    with (out/(a.sample_id+'.plasme_report.csv')).open() as stream:raw=list(csv.DictReader(stream,delimiter='\t'))
    assert {r['contig_id'] for r in rows}=={r['contig'] for r in raw}
    assert all(r['classification']=='plasmid' for r in rows)
    predicted=(out/(a.sample_id+'.plasme.fasta')).read_text()
    if a.expect=='no-hit':
        assert rows==[] and raw==[] and predicted=='' and runtime['candidate_records']==0
    else:
        assert rows and predicted.startswith('>') and runtime['candidate_records']>0
    if a.require_transformer:assert runtime['transformer_scores']>0
    # Independent parser: do not reuse the producer's FASTA/report normalizer.
    reader=('import gzip,json,sys,hashlib\nfrom Bio import SeqIO\n'
            'a,b=sys.argv[1:];s=gzip.open(a,"rt") if a.lower().endswith(".gz") else open(a)\n'
            'source=SeqIO.to_dict(SeqIO.parse(s,"fasta"));s.close()\n'
            'pred=SeqIO.to_dict(SeqIO.parse(b,"fasta"))\n'
            'assert set(pred)<=set(source)\n'
            'assert all(str(v.seq)==str(source[k].seq) for k,v in pred.items())\n'
            'print(json.dumps({"ids":sorted(pred),"lengths":{k:len(v.seq) for k,v in pred.items()},'
            '"DNA_sha256":{k:hashlib.sha256(str(v.seq).encode()).hexdigest() for k,v in pred.items()}}))\n')
    reference=subprocess.run([str(python),'-c',reader,str(assembly),str(out/(a.sample_id+'.plasme.fasta'))],capture_output=True,text=True)
    assert reference.returncode==0,reference.stderr
    independent=json.loads(reference.stdout)
    assert set(independent['ids'])=={r['contig_id'] for r in rows}
    assert sha(assembly)==before
    assert all(sha(Path(name))==value for name,value in sources.items())
    receipt={'pass':True,'command':command,'backend':a.backend,'expect':a.expect,'transformer_required':a.require_transformer,
             'rows':rows,'runtime':runtime,'independent_BioPython':independent,'tasks':tasks,'source_sha256':sources,'assembly_sha256':before,
             'limitations':['Tool/node and output contracts only; not scientific sensitivity/specificity or complete platform certification',
                            'Database identity must be supplied by the corresponding separate locked preparation receipt']}
    (base/'run.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('PASS',a.backend,a.expect,'calls',len(rows),'Transformer scores',runtime['transformer_scores'],flush=True)


if __name__=='__main__':main()
