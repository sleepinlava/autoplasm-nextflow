#!/usr/bin/env python3
"""Actual fixed Platon/full DB controls; original source DNA and predeclared outcomes."""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from Bio import SeqIO

ROOT=Path(__file__).resolve().parents[1]


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as stream:
        for b in iter(lambda:stream.read(1048576),b''):h.update(b)
    return h.hexdigest()


def fasta(p):
    with (gzip.open(p,'rt') if p.read_bytes()[:2]==b'\x1f\x8b' else p.open()) as stream:
        records=list(SeqIO.parse(stream,'fasta'))
    assert len(records)==len({v.id for v in records})
    return {v.id:str(v.seq) for v in records}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['output','prefix','database','positive','negative']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();base=args.output.resolve();base.mkdir(exist_ok=False);prefix=args.prefix.resolve();database=args.database.resolve()
    fixtures=base/'fixtures';fixtures.mkdir();positive=args.positive.resolve();negative=args.negative.resolve()
    zipped=fixtures/'positive.fa.GZ';zipped.write_bytes(gzip.compress(positive.read_bytes(),mtime=0))
    short=fixtures/'short.fa';short.write_text('>short_control\n'+next(iter(fasta(positive).values()))[:800]+'\n')
    duplicate=fixtures/'duplicate.fa';duplicate.write_bytes(positive.read_bytes()+positive.read_bytes())
    bad=fixtures/'corrupt.fa.gz';bad.write_bytes(b'not a gzip file')
    records=[{'id':'P','fasta':str(positive)},{'id':'S.plasme.X','fasta':str(zipped)},{'id':'Negative','fasta':str(negative)}]
    private=base/'database';private.mkdir()
    for p in database.iterdir():
        if p.name=='replication.h3m':shutil.copy2(p,private/p.name)
        else:(private/p.name).symlink_to(p)
    target=private/'replication.h3m';data=target.read_bytes();stat=target.stat();corrupt=b'!'+data[1:]
    def put(value):target.write_bytes(value);os.utime(target,ns=(stat.st_atime_ns,stat.st_mtime_ns))
    (base/'mutation.json').write_text(json.dumps({'before_sha256':hashlib.sha256(data).hexdigest(),'corrupt_sha256':hashlib.sha256(corrupt).hexdigest(),'bytes':len(data),'mtime_ns':stat.st_mtime_ns,'scope':'one private copied HMM only; original full DB unchanged'},indent=2)+'\n')
    sources=['bin/platon_checked.py','modules/detection/platon.nf','envs/platon-linux-64.lock','tests/nextflow/platon_native.nf','tests/run_platon_native.py']
    hashes={p:sha(ROOT/p) for p in sources};runs=[]
    def execute(name,chosen=records,resume=False,failure=None,conda=False):
        folder=base/name;folder.mkdir(exist_ok=resume);config=folder/'config';work=folder/'work';key='platon_'+hashlib.sha256(str(folder).encode()).hexdigest()[:12]
        if not resume:
            config.write_text("params.publish_dir_mode='copy'\nprocess.executor='local'\nprocess.cpus=2\nprocess.memory='4 GB'\nprocess.maxForks=2\nprocess.errorStrategy='terminate'\ndocker.enabled=false\nsingularity.enabled=false\nconda { enabled="+str(conda).lower()+";useMicromamba="+str(conda).lower()+";cacheDir="+repr(str(base/'conda-cache'))+";createOptions='--offline' }\n")
            (folder/'params.json').write_text(json.dumps({'records':chosen,'database':str(private),'outdir':str(folder/'out')},indent=2)+'\n')
        suffix='-bad-resume' if resume and failure else '-resume' if resume else ''
        trace=folder/('trace'+suffix+'.tsv');cmd=[str(ROOT/'results/tool-audit/runtime/bin/nextflow'),'-C',str(config),'run',str(ROOT/'tests/nextflow/platon_native.nf'),'-params-file',str(folder/'params.json'),'-work-dir',str(work),'-with-trace',str(trace),'-ansi-log','false']+(['-resume',key] if resume else ['-name',key])
        env={**os.environ,'PATH':str(prefix/'bin')+':'+os.environ['PATH'],'PYTHONDONTWRITEBYTECODE':'1','CONDA_PKGS_DIRS':str(ROOT/'results/tool-audit/runtime/mamba-root/pkgs'),'MAMBA_ROOT_PREFIX':str(ROOT/'results/tool-audit/runtime/mamba-root')}
        p=subprocess.run(cmd,env=env,text=True,capture_output=True);(folder/('stdout'+suffix+'.log')).write_text(p.stdout);(folder/('stderr'+suffix+'.log')).write_text(p.stderr)
        tasks=list(csv.DictReader(trace.open(),delimiter='\t')) if trace.exists() else [];entry={'case':name+suffix,'command':cmd,'exit_code':p.returncode,'tasks':tasks};runs.append(entry)
        checks={}
        if failure:
            checks['explicit_failure']=p.returncode!=0 and any(t['status']=='FAILED' for t in tasks)
            checks['no_success_emit']='PLATON_PRODUCT=' not in p.stdout
            if resume:
                checks['content_change_invalidates_cache']=not any(t['status']=='CACHED' for t in tasks)
                audits=[json.loads(q.read_text()) for q in work.rglob('*.platon_runtime.json')]
                checks['actual_failed_HMM']=any(any(c.get('exit_code') and 'hmmsearch' in c['command'][0] for c in a.get('failed_children',[])) for a in audits)
            else:
                errors='\n'.join(q.read_text() for q in work.rglob('.command.err'))
                checks['specific_diagnostic']=failure in errors
        else:
            checks['success']=p.returncode==0
            checks['exact_tasks']=len(tasks)==len(chosen) and all(t['status']==('CACHED' if resume else 'COMPLETED') for t in tasks)
            for row in chosen:
                sid=row['id'];out=folder/'out/04_plasmid_detection/platon';state=json.loads((out/(sid+'.platon_state.json')).read_text());audit=json.loads((out/(sid+'.platon_runtime.json')).read_text())
                with (out/(sid+'.platon.tsv')).open() as stream:table=list(csv.DictReader(stream,delimiter='\t'))
                expected=set() if sid in ['Negative','Short'] else {'NC_007941.1'}
                dna=fasta(Path(row['fasta']));pred=fasta(out/(sid+'.plasmid.fasta'))
                checks[sid+'_input_IDs_DNA']=set(pred)==expected and pred=={k:v for k,v in dna.items() if k in expected} and {v['ID'] for v in table}==expected
                checks[sid+'_explicit_state']=state['sample_id']==sid and state['state']==('not_assessed_length_filter' if sid=='Short' else 'no_plasmids' if sid=='Negative' else 'plasmids_found') and state['plasmid_count']==len(expected)
                checks[sid+'_native_audit']=audit['native_exit_code']==0 and not audit['failed_children'] and not audit['worker_errors'] and audit['database_unchanged'] and len(audit['source_sha256'])==7
                if conda:checks['actual_fresh_locked_conda']=str(base/'conda-cache') in audit['python_executable']
        entry['checks']=checks;entry['pass']=all(checks.values());(base/'runs-progress.json').write_text(json.dumps(runs,indent=2)+'\n');print(entry['case'],entry['pass'],checks,flush=True);assert entry['pass'],entry
    try:
        execute('baseline')
        execute('baseline',resume=True)
        put(corrupt);execute('baseline',resume=True,failure='HMM')
        put(data)
        execute('length',[{'id':'Short','fasta':str(short)}])
        execute('corrupt-gzip',[{'id':'Bad','fasta':str(bad)}],failure='gzipped')
        execute('duplicate-ID',[{'id':'Dup','fasta':str(duplicate)}],failure='Duplicate FASTA ID')
        execute('empty',[])
        execute('locked-conda',records[:1],conda=True)
    finally:put(data)
    assert hashes=={p:sha(ROOT/p) for p in sources}
    (base/'run.json').write_text(json.dumps({'pass':True,'runs':runs,'source_sha256':hashes,'limitations':['Actual fixed source/default accuracy/meta/full original v1.5.0 DB; four summary log repairs only, recorded per task. No classifier observer.','pUTI89 reused across plain/gzip/native/Conda/resume is one biological positive; official negative fixture is a software control, not independent classifier sensitivity/specificity validation.','Corrupt private HMM/cache/failure boundaries and short input domain state are not alternative biological methods.','No OCI or full-platform certification.']},indent=2)+'\n')


if __name__=='__main__':main()
