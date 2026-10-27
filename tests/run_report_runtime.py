#!/usr/bin/env python3
"""Native consensus/structure/report provenance and exact-UUID cache controls.

Predictions and DNA are explicit software fixtures, not biological truth or a
classifier benchmark. Only private task-command artifacts are mutated.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_report(base, tasks, dna, version):
    report = next(t for t in tasks if t['name'].endswith('REPORT (report)'))
    data_path = Path(report['workdir']) / 'report_data.json'
    data = json.loads(data_path.read_text())
    assert {r['sample_id']: (r['consensus_plasmids'],r['circular']) for r in data['samples']} == {'S.1':(1,0),'001':(0,0)}
    records = data['runtime_commands']
    assert len(records) == 5
    for task in [t for t in tasks if not t['name'].endswith('REPORT (report)')]:
        folder = Path(task['workdir'])
        copied, = folder.glob('*.task_command.sh')
        original = (folder / '.command.sh').read_bytes()
        assert copied.read_bytes() == original
        record, = [r for r in records if r['task_process'] == task['name'].split(' (')[0] and
                   r['analysis_sample_id'] == task['name'].split(' (')[1][:-1]]
        assert record['script'].encode() == original and record['script_sha256'] == sha(copied)
        assert record['runtime_probe'] == {'command':'Rscript --version','stdout':version}
        assert '--sample-id ' + record['analysis_sample_id'] in record['script']
        assert record['script_sha256'] in data['methods']
        assert record['script_sha256'] in (Path(report['workdir'])/'methods.md').read_text()
        assert record['script_sha256'] in (Path(report['workdir'])/'report.html').read_text()
        if task['name'].startswith('GRAPH_CONSENSUS '):
            assert record['sample_id']=='001' and record['analysis_sample_id']=='gplas_nodes_control_001'
        if task['name']=='PLASMID_CONSENSUS (S.1)':
            fasta=(folder/'S.1.plasmid_contigs.fasta').read_text().splitlines()
            assert fasta[0]=='>p1' and not any(line.startswith('>') for line in fasta[1:])
            assert ''.join(fasta[1:])==dna
        if task['name']=='PLASMID_CONSENSUS (001)':
            assert (folder/'001.plasmid_contigs.fasta').read_bytes()==b''
    assert 'not recorded for every producer' in data['methods']
    assert 'render failed' not in (Path(report['workdir'])/'.command.err').read_text()
    return {'report_data_sha256':sha(data_path),'runtime_commands':5,'source_DNA_and_sample_counts':True,
            'original_script_bytes_sha256_and_direct_R_version':True,'HTML_and_methods_hashes':True,
            'graph_analysis_ID_and_original_sample_ID':True}


def run(base, nextflow):
    fixture=base/'fixtures';fixture.mkdir()
    rng=random.Random(29);dna=''.join(rng.choice('ACGT') for _ in range(1200))
    assert not any(dna[:n]==dna[-n:] for n in range(20,len(dna)))
    (fixture/'samples.tsv').write_text('sample_id\nS.1\n001\n')
    for sid in ['S.1','001']:
        (fixture/(sid+'.fasta')).write_text('>p1\n'+dna+'\n')
        (fixture/(sid+'.summary.tsv')).write_text('seq_name\tplasmid_score\n'+('p1\t0.99\n' if sid=='S.1' else ''))
    config=base/'native.config'
    config.write_text("process.executor='local'\nprocess.cpus=1\nprocess.memory='1 GB'\nprocess.maxForks=1\nprocess.errorStrategy='terminate'\n"
                      "process { withName: GRAPH_CONSENSUS { scratch=true } }\n"
                      "conda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\nparams.publish_dir_mode='copy'\n"
                      "params.consensus_method='weighted_vote'\nparams.consensus_weights='genomad:1'\n"
                      "trace.fields='task_id,hash,name,status,exit,workdir'\n")
    names=['bin/generate_report.R','bin/plasmid_consensus.R','bin/plasmid_structure.R','modules/detection/consensus.nf',
           'modules/detection/structure.nf','modules/cross_sample/report.nf','lib/report_events.nf','assets/plasmid_report.Rmd',
           'tests/nextflow/report_runtime.nf','tests/run_report_runtime.py','envs/r_analysis.yml']
    before={p:sha(ROOT/p) for p in names}
    version=subprocess.run(['Rscript','--version'],capture_output=True,text=True,check=True).stdout.strip()
    env={**os.environ,'PATH':str(ROOT/'bin')+':'+os.environ['PATH']}
    runs=[];uuid=None;target=None;original_bytes=None;original_stat=None;scientific_before=None
    try:
        for case in ['cold','resume','command_corruption','restored']:
            folder=base/case;folder.mkdir()
            if case=='command_corruption':
                modified=original_bytes.replace(b'--sample-id S.1',b'--sample-id X.1')
                assert modified!=original_bytes and len(modified)==len(original_bytes)
                target.write_bytes(modified);os.utime(target,ns=(original_stat.st_atime_ns,original_stat.st_mtime_ns))
                (folder/'tampered-task-command.sh').write_bytes(modified)
            if case=='restored':
                target.write_bytes(original_bytes);os.utime(target,ns=(original_stat.st_atime_ns,original_stat.st_mtime_ns))
            (folder/'params.json').write_text(json.dumps({'fixture_dir':str(fixture),'outdir':str(folder/'out')})+'\n')
            command=[nextflow,'-C',str(config),'run',str(ROOT/'tests/nextflow/report_runtime.nf'),'-params-file',str(folder/'params.json'),
                     '-work-dir',str(base/'work'),'-with-trace',str(folder/'trace.tsv'),'-ansi-log','false','-name','report_runtime_'+case]
            if uuid:command+=['-resume',uuid]
            result=subprocess.run(command,cwd=base,env=env,capture_output=True,text=True,timeout=180)
            (folder/'stdout').write_text(result.stdout);(folder/'stderr').write_text(result.stderr)
            tasks=list(csv.DictReader((folder/'trace.tsv').open(),delimiter='\t')) if (folder/'trace.tsv').exists() else []
            entry={'case':case,'command':command,'exit_code':result.returncode,'tasks':tasks};runs.append(entry)
            (base/'progress.json').write_text(json.dumps({'source_sha256':before,'runs':runs},indent=2)+'\n')
            if case=='command_corruption':
                assert result.returncode!=0 and 'Originating task command checksum mismatch' in result.stdout+result.stderr
                assert Counter(t['status'] for t in tasks)=={'CACHED':5,'FAILED':1}
                assert next(t for t in tasks if t['status']=='FAILED')['name'].endswith('REPORT (report)')
                assert not (folder/'out/report/report_data.json').exists()
                entry['checks']={'same_size_mtime_corruption_rejected_before_report_publication':True}
            else:
                assert result.returncode==0,result.stdout+result.stderr
                assert len(tasks)==6 and all(t['status']==('COMPLETED' if case=='cold' else 'CACHED') for t in tasks)
                entry['checks']=check_report(folder,tasks,dna,version)
                if case=='cold':
                    row=next(l.split('\t') for l in reversed((base/'.nextflow/history').read_text().splitlines()) if '\treport_runtime_cold\t' in l)
                    uuid=row[5]
                    task=next(t for t in tasks if t['name']=='PLASMID_CONSENSUS (S.1)')
                    target=Path(task['workdir'])/'S.1.PLASMID_CONSENSUS.task_command.sh'
                    original_bytes=target.read_bytes();original_stat=target.stat()
                    scientific_before={str(p):sha(p) for p in (base/'work').rglob('*') if p.is_file() and not p.is_symlink() and p.suffix in ['.fasta','.tsv']}
                if case=='restored':assert entry['checks']['report_data_sha256']==runs[0]['checks']['report_data_sha256']
            assert before=={p:sha(ROOT/p) for p in names}
            if scientific_before:assert all(sha(p)==h for p,h in scientific_before.items())
            print(case,Counter(t['status'] for t in tasks),flush=True)
    finally:
        if target is not None and original_bytes is not None:
            target.write_bytes(original_bytes);os.utime(target,ns=(original_stat.st_atime_ns,original_stat.st_mtime_ns))
    receipt={'pass':True,'runs':runs,'cold_uuid':uuid,'source_sha256':before,'source_unchanged':True,
             'scientific_products_unchanged':True,'native_Rscript_version':version,
             'scope':'Five actual consensus/structure R tasks (one scratch graph-entity control) and native R Markdown report; exact command bytes/digests/probe stdout/sample identity, cache and corruption rejection.',
             'limitations':['Explicit controlled DNA/predictions, no native classifier inference or biological benchmark.','Production capture currently covers consensus/structure only; all other producers and database/model identities remain TA-016 incomplete.','Native local26.10 only; no Conda/image/remote/AWS or full-platform certification.']}
    (base/'run.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--work-dir',required=True)
    parser.add_argument('--nextflow',default=shutil.which('nextflow') or str(ROOT/'results/tool-audit/runtime/bin/nextflow'))
    args=parser.parse_args();base=Path(args.work_dir).resolve();base.mkdir(parents=True)
    run(base,args.nextflow)
