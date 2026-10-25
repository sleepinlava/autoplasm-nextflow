#!/usr/bin/env python3
"""Actual fixed SPAdes module exports the same-task three-file PlasMAAG bundle."""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    args = parser.parse_args(); base=args.output.resolve(); base.mkdir(exist_ok=False)
    prefix=args.prefix.resolve(); dataset=prefix/'share/spades/test_dataset'
    reads=[dataset/f'ecoli_1K_{i}.fq.gz' for i in [1,2]]
    config=base/'config';config.write_text("includeConfig '"+str(ROOT/'conf/plasmaag.config')+"'\nprocess.executor='local'\nprocess.cpus=2\nprocess.memory='2 GB'\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\ntrace.fields='task_id,hash,name,status,exit,workdir'\nprocess { withName:'METASPADES' { ext.args='--meta --only-assembler -k 21,33'; ext.prefix='fixture' } }\n")
    params=base/'params.json';params.write_text(json.dumps(dict(read1=str(reads[0]),read2=str(reads[1]),plasmid_binning_tools=['plasmaag'])))
    names=['modules/nf-core/spades/main.nf','bin/spades_graph_provenance.py','conf/plasmaag.config','tests/nextflow/spades_plasmaag_bundle.nf']
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();before={n:sha(ROOT/n) for n in names}
    cmd=[str(ROOT/'results/tool-audit/runtime/bin/nextflow'),'-C',str(config),'run',str(ROOT/'tests/nextflow/spades_plasmaag_bundle.nf'),'-params-file',str(params),'-work-dir',str(base/'work'),'-with-trace',str(base/'trace.tsv'),'-ansi-log','false']
    env={**os.environ,'PATH':str(prefix/'bin')+':'+os.environ['PATH']}
    result=subprocess.run(cmd,env=env,text=True,capture_output=True,timeout=600)
    (base/'stdout').write_text(result.stdout);(base/'stderr').write_text(result.stderr)
    tasks=list(csv.DictReader((base/'trace.tsv').open(),delimiter='\t')) if (base/'trace.tsv').exists() else []
    record=dict(command=cmd,exit_code=result.returncode,tasks=tasks,source_sha256=before,source_unchanged=before=={n:sha(ROOT/n) for n in names},reads_sha256={p.name:sha(p) for p in reads})
    (base/'progress.json').write_text(json.dumps(record,indent=2)+'\n')
    assert result.returncode==0 and len(tasks)==1 and tasks[0]['status']=='COMPLETED',record
    work=Path(tasks[0]['workdir']);bundle=work/'fixture.plasmaag_spades';checks={}
    with gzip.open(work/'fixture.contigs.fa.gz','rb') as stream:checks['raw_full_contigs_match_gz_export']=stream.read()==(bundle/'contigs.fasta').read_bytes()
    for name in ['contigs.paths','assembly_graph_after_simplification.gfa']:checks[name]=sha(bundle/name)==sha(work/name) and (bundle/name).stat().st_size>0
    checks['channel_emitted']='PLASMAAG_BUNDLE=fixture:' in result.stdout
    record.update(checks=checks,bundle_sha256={p.name:sha(p) for p in bundle.iterdir()},scope='Native SPAdes4.1.0 official1K fixture; same-successful-task complete contigs/paths/GFA, not assembly accuracy or PlasMAAG method validation')
    record['pass']=record['source_unchanged'] and all(checks.values());(base/'run.json').write_text(json.dumps(record,indent=2)+'\n');assert record['pass']


if __name__=='__main__':main()
