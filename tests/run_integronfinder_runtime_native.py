#!/usr/bin/env python3
"""Full original ACBA fixture: real production cache and topology controls."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from module_harness import run_session_uuid

ROOT=Path(__file__).resolve().parents[1]


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def table(p): return list(csv.DictReader([s for s in p.read_text().splitlines() if not s.startswith('#')],delimiter='\t'))


def run(base,prefix,fixture):
    base.mkdir(parents=True,exist_ok=False)
    package=prefix/'lib/python3.14/site-packages/integron_finder'
    private=base/'private-python/integron_finder'
    shutil.copytree(package,private,ignore=shutil.ignore_patterns('__pycache__'))
    watched=[p for p in sorted(private.rglob('*')) if p.is_file()]
    originals={p:(p.read_bytes(),p.stat()) for p in watched}
    for p in watched:
        source=package/p.relative_to(private)
        assert sha(p)==sha(source) and (p.stat().st_dev,p.stat().st_ino)!=(source.stat().st_dev,source.stat().st_ino)
    env=dict(os.environ,PATH=str(prefix/'bin')+':'+os.environ['PATH'],PYTHONPATH=str(private.parent),PYTHONDONTWRITEBYTECODE='1',MPLCONFIGDIR=str(base/'mplconfig'),OPENBLAS_NUM_THREADS='2',OMP_NUM_THREADS='2')
    golden={}
    # Independent original executable with explicit original topology options.
    for mode,flags in [('linear',['--linear']),('circular',['--circ'])]:
        case=base/('original-'+mode);case.mkdir()
        cmd=[str(prefix/'bin/integron_finder'),'--cpu','2','--outdir',str(case),*flags,str(fixture)]
        p=subprocess.run(cmd,env=dict(env,PYTHONPATH=''),capture_output=True,text=True,timeout=120)
        (case/'stdout').write_text(p.stdout);(case/'stderr').write_text(p.stderr)
        assert p.returncode==0,p.stderr
        out=case/'Results_Integron_Finder_acba.007.p01.13'
        golden[mode]={kind:table(out/('acba.007.p01.13.'+kind)) for kind in ['integrons','summary']}
        (case/'command.json').write_text(json.dumps(cmd))
    assert golden['linear']['summary'][0]['CALIN']=='1' and golden['linear']['summary'][0]['In0']=='1'
    assert golden['circular']['summary'][0]['complete']=='1'
    config=base/'config'
    positive="process { executor='local';cpus=2;memory='2 GB';errorStrategy='terminate';maxRetries=0 }\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\ntrace.fields='task_id,hash,name,status,exit,workdir'\n"
    config.write_text(positive)
    (base/'params.json').write_text(json.dumps(dict(fasta=str(fixture))))
    sources=['tests/run_integronfinder_runtime_native.py','tests/nextflow/integronfinder_runtime_native.nf','bin/integronfinder_runtime_resources.py','bin/integronfinder_topology.py','lib/integronfinder_runtime.nf','modules/nf-core/integronfinder/main.nf']
    before={p:sha(ROOT/p) for p in sources}
    runs=[];session=None
    def execute(name,status,mode='linear'):
        nonlocal session
        case=base/name;case.mkdir();trace=case/'trace.tsv'
        cmd=[str(ROOT/'results/tool-audit/runtime/bin/nextflow'),'-C',str(config),'run',str(ROOT/'tests/nextflow/integronfinder_runtime_native.nf'),'-params-file',str(base/'params.json'),'-work-dir',str(base/'work'),'-with-trace',str(trace),'-ansi-log','false']
        cmd+=['-name','integronfinder_runtime_native'] if session is None else ['-resume',session]
        p=subprocess.run(cmd,cwd=base,env=env,capture_output=True,text=True,timeout=180)
        (case/'stdout').write_text(p.stdout);(case/'stderr').write_text(p.stderr)
        tasks=list(csv.DictReader(trace.open(),delimiter='\t')) if trace.exists() else []
        record=dict(case=name,command=cmd,exit_code=p.returncode,tasks=tasks);runs.append(record)
        (base/'progress.json').write_text(json.dumps(runs,indent=2)+'\n')
        if status=='CONTEXT_REFUSED':
            assert p.returncode!=0 and len(tasks)==1 and tasks[0]['status']=='COMPLETED',record
            assert 'runtime mismatch before cache lookup' in p.stdout+p.stderr
            record['no_consumer_submitted']=True
        else:
            assert len(tasks)==2 and ((p.returncode==0)==(status!='FAILED')),record
            probe=next(t for t in tasks if t['name'].startswith('INTEGRONFINDER_RESOURCE_PROBE'))
            consumer=next(t for t in tasks if t['name'].startswith('INTEGRONFINDER ('))
            assert probe['status']=='COMPLETED' and consumer['status']==status,record
            identity_path=Path(probe['workdir'])/'integronfinder_runtime_identity.json'
            identity=json.loads(identity_path.read_text())
            assert identity['resolved_locations']['package']==str(private)
            assert identity['topology']['replicons'][0]['topology']==('lin' if mode=='linear' else 'circ')
            record.update(consumer_hash=consumer['hash'],identity_sha256=sha(identity_path))
            if status=='FAILED':
                log=(Path(consumer['workdir'])/'.command.log').read_text()
                assert 'cmsearch' in log and 'returncode' in log,log[-1500:]
            else:
                out=Path(consumer['workdir'])/'Results_Integron_Finder_acba.007.p01.13'
                for kind in ['summary','integrons']:
                    assert table(out/('acba.007.p01.13.'+kind))==golden[mode][kind],kind
                record['full_original_native_tables_equal']=True
        if session is None: session=run_session_uuid('integronfinder_runtime_native',base)
        print(name,status,flush=True)
    def restore():
        for p,(data,st) in originals.items():
            p.write_bytes(data);p.chmod(st.st_mode&0o7777);os.utime(p,ns=(st.st_atime_ns,st.st_mtime_ns))
    def mutate(p,data):
        st=originals[p][1];assert len(data)==st.st_size
        p.write_bytes(data);os.utime(p,ns=(st.st_atime_ns,st.st_mtime_ns))
        assert p.stat().st_size==st.st_size and p.stat().st_mtime_ns==st.st_mtime_ns
    try:
        execute('cold','COMPLETED');execute('unchanged','CACHED')
        for label,name in [('integrase','integron_integrase.hmm'),('attc','attc_4.cm')]:
            p=private/'data/Models'/name;data=bytearray(originals[p][0]);i=data.index(b'DATE ')+5
            while data[i]==32:i+=1
            data[i]=ord('X')
            mutate(p,bytes(data));execute(label+'-date-change','COMPLETED');restore();execute(label+'-restored','CACHED')
        cm=private/'data/Models/attc_4.cm';data=bytearray(originals[cm][0]);data[0]=ord('X');mutate(cm,bytes(data));execute('corrupt-CM','FAILED')
    finally: restore()
    execute('all-restored','CACHED')
    circle=positive+"\nprocess { withName: 'INTEGRONFINDER|INTEGRONFINDER_RESOURCE_PROBE' { ext.args='--circ' } }\n"
    config.write_text(circle);execute('explicit-circular','COMPLETED','circular');execute('explicit-circular-unchanged','CACHED','circular')
    for name,setting in [('args',"ext.args='--linear'"),('beforeScript',"beforeScript='export INTEGRON_CONTEXT_ONLY=1'")]:
        config.write_text(circle+"\nprocess { withName:'INTEGRONFINDER' { "+setting+" } }\n");execute('mismatch-'+name,'CONTEXT_REFUSED','circular')
    config.write_text(positive)
    assert runs[0]['consumer_hash']==runs[1]['consumer_hash']==runs[3]['consumer_hash']==runs[5]['consumer_hash']==runs[7]['consumer_hash']
    for p in watched:
        source=package/p.relative_to(private);assert sha(p)==sha(source) and (p.stat().st_mode&0o7777)==(source.stat().st_mode&0o7777)
    assert before=={p:sha(ROOT/p) for p in sources}
    (base/'run.json').write_text(json.dumps(dict(pass_checks=True,runs=runs,source_sha256=before,source_unchanged=True,session_uuid=session,private_resources_restored=True,original_package_sha256={str(p.relative_to(private)):sha(p) for p in watched},fixture_sha256=sha(fixture),scope='Actual production2.0.5, full original20739-byte/20301bp ACBA replicon. Approved unknown-linear policy compared exact original --linear tables; explicit --circ exact original circular tables. Full models, same-stat HMM/CM metadata mutation/restore, real cmsearch corruption/context failure; not biological accuracy/full environment/OCI/platform certificate.'),indent=2)+'\n')
    print('PASS production IntegronFinder resources/topology/cache',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--prefix',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True);a=p.parse_args();run(a.out.resolve(),a.prefix.resolve(),a.fixture.resolve())
