#!/usr/bin/env python3
"""Verify real fresh Nextflow environment evidence plus both MOB YAML/cache paths.

Requires a completed initial cold environment creation, so it never restarts a
live or missing-observation job. No MOB classification or DB initialization.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
from module_harness import run_session_uuid

ROOT=Path(__file__).resolve().parents[1]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def run(output,initial,wheel_manifest):
    output.mkdir(parents=True,exist_ok=False)
    original=json.loads((initial/'run.json').read_text());assert original['exit_code']==0
    original_sources=json.loads((initial/'source-before.json').read_text())
    assert all(sha(ROOT/p)==s for p,s in original_sources.items())
    tasks=list(csv.DictReader((initial/'trace.tsv').open(),delimiter='\t'))
    assert len(tasks)==1 and tasks[0]['status']=='COMPLETED'
    assert '-resume' not in original['command']
    assert 'Creating env using micromamba:' in ((initial/'stdout').read_text()+(initial/'stderr').read_text())
    config_text=(initial/'config').read_text()
    assert 'createOptions' not in config_text and 'skip-run-link-scripts' not in config_text
    wheel=json.loads(wheel_manifest.read_text())
    hashes={str(Path(k).relative_to('mob_suite')):v['wheel_sha256'] for k,v in wheel['comparisons'].items()}
    sources=['modules/nf-core/mobsuite/recon/environment.yml','modules/nf-core/mobsuite/typer/environment.yml','tests/nextflow/mobsuite_software.nf','tests/run_mobsuite_software.py','bin/mobsuite_preflight.py','tests/test_mobsuite_preflight.py']
    before={p:sha(ROOT/p) for p in sources};assert before[sources[0]]==before[sources[1]]
    history=(initial/'.nextflow/history').read_text().splitlines();assert len(history)==1
    first_session=history[0].split('\t')[5]
    env=dict(os.environ,MAMBA_ROOT_PREFIX=str(ROOT/'results/tool-audit/runtime/mamba-root'),PYTHONDONTWRITEBYTECODE='1')
    runs=[]
    def validate(record):
        task=record['tasks'][0];work=Path(task['workdir']);identity=json.loads((work/'readiness.json').read_text())
        assert identity['python_sources']==hashes
        assert identity['direct_url']['archive_info']['hashes']['sha256']==wheel['sha256']
        assert identity['default_database_files']==['__init__.py'] and not any(p['name']=='mob_suite' for p in identity['conda_packages'])
        assert all(v.endswith('3.1.9') for v in identity['versions'].values())
        record.update(prefix=identity['prefix'],readiness_sha256=sha(work/'readiness.json'),no_conda_mob_package=True,all16_sources_equal_wheel=True)
        return identity
    cold=dict(case='original-recon-cold',command=original['command'],exit_code=0,tasks=tasks)
    identity=validate(cold);runs.append(cold)
    def execute(name,module,status,resume=None):
        case=output/name;case.mkdir();trace=case/'trace.tsv'
        cmd=[str(ROOT/'results/tool-audit/runtime/bin/nextflow'),'-C',str(initial/'config'),'run',str(ROOT/'tests/nextflow/mobsuite_software.nf'),'--environment',str(ROOT/'modules/nf-core/mobsuite'/module/'environment.yml'),'-work-dir',str(initial/'work'),'-with-trace',str(trace),'-ansi-log','false']
        cmd+=['-resume',resume] if resume else ['-name','mobsuite_typer_software']
        p=subprocess.run(cmd,cwd=initial,env=env,capture_output=True,text=True,timeout=300)
        (case/'stdout').write_text(p.stdout);(case/'stderr').write_text(p.stderr)
        actual=list(csv.DictReader(trace.open(),delimiter='\t'));record=dict(case=name,command=cmd,exit_code=p.returncode,tasks=actual);runs.append(record)
        (output/'progress.json').write_text(json.dumps(runs,indent=2)+'\n');assert p.returncode==0 and len(actual)==1 and actual[0]['status']==status,record
        validate(record);print(name,status,flush=True)
    execute('recon-unchanged','recon','CACHED',first_session)
    execute('typer-cold','typer','COMPLETED')
    typer_session=run_session_uuid('mobsuite_typer_software',initial)
    execute('typer-unchanged','typer','CACHED',typer_session)
    prefix=Path(identity['prefix'])
    checks=[]
    for name,cmd in [('pip-check',[str(prefix/'bin/python'),'-m','pip','check']),('preflight-unit',[str(prefix/'bin/python'),str(ROOT/'tests/test_mobsuite_preflight.py'),'-v'])]:
        p=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=120);(output/(name+'.stdout')).write_text(p.stdout);(output/(name+'.stderr')).write_text(p.stderr);checks.append(dict(case=name,command=cmd,exit_code=p.returncode));assert p.returncode==0,p.stderr
    assert before=={p:sha(ROOT/p) for p in sources}
    assert all(record['prefix']==str(prefix) for record in runs)
    result=dict(pass_bounded_provider_checks=True,formal_acceptance=False,source_sha256=before,initial_source_sha256=original_sources,runs=runs,checks=checks,unique_unit_methods=8,scope='Real Nextflow Micromamba fresh software environment plus recon/typer declaration and task-cache recovery.4trace:2COMPLETED version-only tasks+2CACHED, not native classification. No global link-script skipping, no Conda mob_suite package; official immutable wheel16source files exact. DB uninitialized, no biological DB/model/science execution. Plain Conda/Mamba/OCI/provider/full reference/cache integration remain unverified.')
    (output/'run.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--initial',type=Path,required=True);p.add_argument('--wheel-manifest',type=Path,required=True);a=p.parse_args();run(a.output.resolve(),a.initial.resolve(),a.wheel_manifest.resolve())
