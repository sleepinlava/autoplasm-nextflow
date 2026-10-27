#!/usr/bin/env python3
"""Reproducible native MOB CLI/read-only preflight checks, never MOB classification."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def run(output,prefix,fixture):
    output.mkdir(parents=True,exist_ok=False)
    assert fixture.is_file()
    sources=['bin/mobsuite_preflight.py','tests/test_mobsuite_preflight.py','tests/run_mobsuite_preflight.py','tests/mobsuite-native.lock.json']
    before={p:sha(ROOT/p) for p in sources}
    env=dict(os.environ,PATH=str(prefix/'bin')+':'+os.environ['PATH'],PYTHONDONTWRITEBYTECODE='1')
    database=prefix/'lib/python3.10/site-packages/mob_suite/databases'
    def state():return {str(p.relative_to(database)):sha(p) for p in database.rglob('*') if p.is_file() and '__pycache__' not in p.relative_to(database).parts}
    initial=state();assert sorted(initial)==['__init__.py']
    runs=[]
    def execute(name,cmd,expected):
        case=output/name;case.mkdir();p=subprocess.run(cmd,env=env,cwd=ROOT,capture_output=True,text=True,timeout=120)
        (case/'stdout').write_text(p.stdout);(case/'stderr').write_text(p.stderr)
        row=dict(case=name,command=cmd,exit_code=p.returncode);runs.append(row)
        (output/'progress.json').write_text(json.dumps(runs,indent=2)+'\n');assert p.returncode==expected,row
        return p
    for name,argv in [('version',['mob_recon','--version']),('help',['mob_recon','--help']),('mash-version',['mash','--version']),('blast-version',['blastn','-version'])]:
        p=execute(name,[str(prefix/'bin'/argv[0]),*argv[1:]],0)
        if name=='version':assert p.stdout.strip()=='mob_recon 3.1.9'
    for name,extra,reason in [('default',[],'automatic initialization is prohibited'),('custom',['-d',str(output/'UNPREPARED_DB')],'missing/empty')]:
        target=output/(name+'-SHOULD_NOT_EXIST');receipt=output/(name+'-NO_SUCCESS_RECEIPT.json')
        cmd=[str(prefix/'bin/python'),str(ROOT/'bin/mobsuite_preflight.py'),'--output',str(receipt),'--','--infile',str(fixture),'--outdir',str(target),*extra]
        p=execute(name+'-refusal',cmd,2)
        assert reason in p.stderr and not target.exists() and not receipt.exists()
    execute('unit',[str(prefix/'bin/python'),str(ROOT/'tests/test_mobsuite_preflight.py'),'-v'],0)
    assert state()==initial and before=={p:sha(ROOT/p) for p in sources}
    result=dict(pass_bounded_preflight_checks=True,formal_acceptance=False,source_sha256=before,runs=runs,unit_unique_methods=8,native_scientific_tasks=0,default_database_files_unchanged=True,fixture_sha256=sha(fixture),scope='Actual installed3.1.9 CLI help/version +2read-only preparation refusals and8unique structural-control unit methods. Positive SQLite control is explicitly synthetic metadata with nonbiological placeholder resources; no scientific DB validity or MOB classification/cache/production integration acceptance. No mob_init/ETE object/download/scientific child invoked. Complete original bacterial540bp fixture supplied to refusals without changing its bytes.')
    (output/'run.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(cli_readiness_commands=6,unique_unit_methods=8,native_science=0)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--prefix',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True);a=p.parse_args();run(a.output.resolve(),a.prefix.resolve(),a.fixture.resolve())
