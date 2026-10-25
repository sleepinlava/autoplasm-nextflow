#!/usr/bin/env python3
"""Original downstream workflow, explicit DNA-driven COPLA observer; no classification."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from test_copla_candidates import OBSERVER

ROOT=Path(__file__).resolve().parents[1]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work-dir',type=Path,required=True);p.add_argument('--prefix',type=Path,required=True)
    a=p.parse_args();base=a.work_dir.resolve();base.mkdir(parents=True,exist_ok=False)
    source_names=['subworkflows/plasmid_downstream.nf','modules/typing/copla.nf','bin/run_copla_candidates.py',
                  'tests/nextflow/copla_downstream.nf','tests/run_copla_routing.py','tests/test_copla_candidates.py']
    sources={n:sha(ROOT/n) for n in source_names};fixture=base/'fixture';fixture.mkdir()
    first=fixture/'one.fna';first.write_text('>shared\nACGTACGT\n>extra\nTTTTCCCCAAAAGGGG\n')
    second=fixture/'two.fna';second.write_text('>shared\nTTTTCCCCAAAAGGGG\n')
    before={str(f):sha(f) for f in [first,second]}
    config=base/'config';config.write_text("process.executor='local'\nprocess.cpus=1\nprocess.memory='2 GB'\n"
            "conda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\npodman.enabled=false\n"
            "params.publish_dir_mode='copy'\ntrace.fields='task_id,hash,name,status,exit,workdir'\n")
    runs=[]
    for name in ['disabled','enabled','second-candidate-fails','missing-prediction','external-reference']:
        case=base/name;case.mkdir();install=case/"observer installation's directory";(install/'bin').mkdir(parents=True)
        (install/'bin/copla.py').write_text(OBSERVER);(install/'bin/ani.rb').write_text('# observer only\n')
        for resource in ['Copla_RS84','MOBscan_171004','MacSyFinder_190530/Conjugation','PlasmidFinder_190731','CARD_201015']:
            (install/'databases'/resource).mkdir(parents=True)
        ref=install/'databases/Copla_RS84/REF.1.fna';ref.write_text('>REF.1\nACGT\n')
        reflist=case/'list.fofn';reflist.write_text(str(second if name=='external-reference' else ref)+'\n')
        graph=case/'graph.pickle';graph.write_text('OBSERVER ONLY: NOT A SCIENTIFIC GRAPH\n')
        macsy=case/'macsy';(macsy/'bin').mkdir(parents=True);(macsy/'bin/macsyfinder').write_text('# observer only\n')
        if name=='second-candidate-fails':(install/'bin/fail_second').touch()
        if name=='missing-prediction':(install/'bin/missing_prediction').touch()
        positive=name in ['enabled','disabled']
        records=[{'id':'S1','fasta':str(first)},{'id':'S.2','fasta':str(second)}] if positive else [{'id':'S1','fasta':str(first)}]
        params={n:[] for n in ['typing_tools','annotation_tools','annotation_optional_tools','plasmid_binning_tools']}
        params.update(records=records,outdir=str(case/'out'),typing_optional_tools=[] if name=='disabled' else [' copla '],
                      copla_refgraph=str(graph),copla_reflist=str(reflist),copla_dir=str(install),copla_macsyfinder_dir=str(macsy))
        (case/'params.json').write_text(json.dumps(params))
        command=[shutil.which('nextflow') or 'nextflow','-C',str(config),'run',str(ROOT/'tests/nextflow/copla_downstream.nf'),
                 '-params-file',str(case/'params.json'),'-work-dir',str(case/'work'),'-with-trace',str(case/'trace.tsv'),'-ansi-log','false']
        result=subprocess.run(command,cwd=case,env={**os.environ,'PATH':str(a.prefix.resolve()/'bin')+os.pathsep+os.environ['PATH']},capture_output=True,text=True)
        (case/'console.log').write_text(result.stdout+result.stderr)
        with (case/'trace.tsv').open() as f:tasks=list(csv.DictReader(f,delimiter='\t'))
        out=case/'out/06_plasmid_typing/copla';events=[]
        if positive:
            assert result.returncode==0,result.stdout+result.stderr
            lines=[line.split('COPLA_REPORT_EVENTS ',1)[1] for line in result.stdout.splitlines() if line.startswith('COPLA_REPORT_EVENTS ')]
            assert len(lines)==1;events=json.loads(lines[0])
            if name=='disabled':assert not tasks and not list(out.glob('*')) and events==[]
            else:
                assert len(tasks)==2 and all(t['status']=='COMPLETED' for t in tasks)
                expected={'S1':[('shared','8','PTU-A'),('extra','16','PTU-B')],'S.2':[('shared','16','PTU-B')]}
                for sid,truth in expected.items():
                    with (out/(sid+'.copla.tsv')).open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
                    assert [(r['contig_id'],r['length'],r['predicted_ptu']) for r in rows]==truth
                    manifest=json.loads((out/(sid+'.copla/entities.json')).read_text());assert len(manifest['entities'])==len(truth)
                    assert not manifest['source_patch']['applied']
                assert len(events)==4 and all(e[0]['producer']=='COPLA' and e[0]['kind']=='evidence' for e in events)
                assert {e[0]['output'] for e in events}=={'typing','raw'}
                assert sorted(e[0]['evidence'][0]['id'] for e in events)==['S.2','S.2','S1','S1']
        else:
            assert result.returncode!=0 and len(tasks)==1 and tasks[0]['status']=='FAILED'
            assert not list(out.glob('*'))
            errors={'second-candidate-fails':'failed for candidate extra','missing-prediction':'Missing exact COPLA product','external-reference':'outside the declared installation'}
            assert errors[name] in (Path(tasks[0]['workdir'])/'.command.err').read_text()
        assert all(sha(Path(f))==h for f,h in before.items())
        assert all(sha(ROOT/n)==h for n,h in sources.items())
        runs.append({'case':name,'command':command,'exit':result.returncode,'tasks':tasks,'events':events,'pass':True})
        (base/'run.json').write_text(json.dumps({'pass':len(runs)==5,'runs':runs,'source_sha256':sources,
              'scope':'Explicit DNA-driven compatible COPLA CLI observers through the original downstream workflow; shared IDs with different DNA, exact products, atomic failures and report evidence. No graph/ANI/model inference.'},indent=2)+'\n')
        print('PASS',name,flush=True)


if __name__=='__main__':main()
