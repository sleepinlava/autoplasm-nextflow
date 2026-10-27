#!/usr/bin/env python3
"""Real production entrypoint refusals and separate stubs; no native MOB science."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def run(base,prefix,fixture):
    base.mkdir(parents=True,exist_ok=False);empty=base/'EMPTY_UNPREPARED_DATABASE';empty.mkdir()
    env=dict(os.environ,PATH=str(prefix/'bin')+':'+os.environ['PATH'],PYTHONDONTWRITEBYTECODE='1')
    sources=['tests/run_mobsuite_execution_guard.py','tests/nextflow/mobsuite_guard_native.nf','bin/mobsuite_preflight.py','lib/mobsuite_runtime.nf','modules/nf-core/mobsuite/recon/main.nf','modules/nf-core/mobsuite/typer/main.nf']
    before={p:sha(ROOT/p) for p in sources}
    database=prefix/'lib/python3.10/site-packages/mob_suite/databases'
    def state():return {str(p.relative_to(database)):sha(p) for p in database.rglob('*') if p.is_file() and '__pycache__' not in p.relative_to(database).parts}
    original=state();assert sorted(original)==['__init__.py']
    runs=[]
    for mode in ['recon','annotation','typer']:
        for scenario in ['default-refusal','explicit-refusal','stub']:
            case=base/(mode+'-'+scenario);case.mkdir();config=case/'config'
            text="process { executor='local';cpus=1;memory='1 GB';errorStrategy='terminate';maxRetries=0 }\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\ntrace.fields='task_id,hash,name,status,exit,workdir'\n"
            if scenario=='explicit-refusal' and mode!='typer':text+="process { withName: 'MOB_RECON|MOB_SUITE_ANNOT' { ext.args='--database_directory "+str(empty)+"' } }\n"
            config.write_text(text)
            cmd=[str(ROOT/'results/tool-audit/runtime/bin/nextflow'),'-C',str(config),'run',str(ROOT/'tests/nextflow/mobsuite_guard_native.nf'),'--mode',mode,'--fasta',str(fixture),'-work-dir',str(base/'work'),'-with-trace',str(case/'trace.tsv'),'-ansi-log','false']
            if scenario=='explicit-refusal' and mode=='typer':cmd+=['--database',str(empty)]
            if scenario=='stub':cmd.append('-stub-run')
            proc=subprocess.run(cmd,cwd=base,env=env,capture_output=True,text=True,timeout=180);(case/'stdout').write_text(proc.stdout);(case/'stderr').write_text(proc.stderr)
            tasks=list(csv.DictReader((case/'trace.tsv').open(),delimiter='\t'))
            record=dict(case=mode+'-'+scenario,command=cmd,exit_code=proc.returncode,tasks=tasks);runs.append(record);(base/'progress.json').write_text(json.dumps(runs,indent=2)+'\n')
            assert len(tasks)==1,record;task=tasks[0];work=Path(task['workdir'])
            if scenario=='stub':
                assert proc.returncode==0 and task['status']=='COMPLETED',record
                assert not (work/'mobsuite_preflight.json').exists()
                assert all(p.stat().st_size==0 for p in work.rglob('*.txt') if not p.is_symlink())
                record['stub_interface_only']=True
            else:
                assert proc.returncode!=0 and task['status']=='FAILED' and task['exit']=='2',record
                log=(work/'.command.log').read_text();reason='automatic initialization is prohibited' if scenario=='default-refusal' else 'Required prepared resources missing/empty'
                assert reason in log,log
                assert not (work/'results').exists() and not (work/'bacterial_control.txt').exists() and not (work/'mobsuite_preflight.json').exists()
                record.update(preparation_refused=True,no_scientific_outputs=True)
            assert state()==original and not any(empty.iterdir())
            print(record['case'],task['status'],flush=True)
    assert before=={p:sha(ROOT/p) for p in sources}
    result=dict(pass_bounded_execution_guard_checks=True,formal_acceptance=False,source_sha256=before,runs=runs,default_db_files_unchanged=True,explicit_empty_db_unchanged=True,fixture_sha256=sha(fixture),scope='Three actual production aliases, default and explicit unprepared DB refusals:6real FAILED tasks before native scientific main;3separate stubs complete. Complete original bacterial540bp fixture unchanged. No biological DB/virus/model download or MOB science. Cache identity/complete reference/valid scientific positives/OCI/provider remain pending.')
    (base/'run.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--prefix',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True);a=p.parse_args();run(a.output.resolve(),a.prefix.resolve(),a.fixture.resolve())
