#!/usr/bin/env python3
"""Main-entry PlasMAAG resource/platform controls and real cohort input rejections."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--source',type=Path,required=True)
    args=parser.parse_args();base=args.output.resolve();base.mkdir(exist_ok=False)
    data=base/'input.fastq';data.write_text('@pair\nACGT\n+\nIIII\n')
    r2=base/'read2.fastq';r2.write_bytes(data.read_bytes());assembly=base/'assembly.fasta';assembly.write_text('>contig\nACGT\n')
    sheet=base/'samples.tsv';sheet.write_text('sample_id\tgroup\tread1\tread2\tlong_reads\tassembly\nA.1\tgroup0\t'+'\t'.join([str(data),str(r2),str(data),str(assembly)])+'\n')
    options={key:[] for key in ['polishing_tools','typing_tools','typing_optional_tools','host_prediction_tools','mag_tools','host_linking_methods','host_linking_optional_methods','annotation_tools','annotation_optional_tools','comparative_tools','comparative_optional_tools']}
    options.update(platform='illumina',short_read_assembler='metaspades',hybrid_assembler='hybridspades',plasmid_binning_tools=['plasmaag'],plasmid_detection_tools=['genomad'],genomad_db=str(base),plasmaag_source=str(args.source.resolve()),plasmaag_genomad_splits=0,samplesheet=str(sheet),host_plasmid_linking=False)
    cases=[('missing-source',dict(options,plasmaag_source=None),'an enabled tool requires --plasmaag_source',False)]
    for platform in ['ont','pacbio_hifi','assembly','hybrid']:
        cases.append((platform,dict(options,platform=platform),'PlasMAAG requires illumina with metaspades or megahit',False))
    cases += [('missing-source-layout',dict(options,plasmaag_source=str(base)),'--plasmaag_source missing fixed source file PlasMAAG/__main__.py',False),
              ('negative-splits',dict(options,plasmaag_genomad_splits=-1),'--plasmaag_genomad_splits must be a nonnegative integer',False),
              ('whitespace-prefix',dict(options,plasmaag_conda_prefix='bad cache'),'--plasmaag_conda_prefix must not contain whitespace',False),
              ('metaspades-preview',options,'',True),('megahit-preview',dict(options,short_read_assembler='megahit'),'',True)]
    hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['main.nf','subworkflows/plasmaag_binning.nf']}

    def execute(case,workflow='main.nf',minimal=False):
        name,params,diagnostic,preview=case;folder=base/name;folder.mkdir();pf=folder/'params.json';pf.write_text(json.dumps(dict(params,outdir=str(folder/'out'))))
        config=ROOT/'results/tool-audit/20261020-main-p0/combined.config'
        if minimal:
            config=folder/'config';config.write_text("process.executor='local'\nprocess.cpus=1\nprocess.memory='256 MB'\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\nparams.publish_dir_mode='copy'\ntrace.fields='task_id,hash,name,status,exit,workdir'\n")
        trace=folder/'trace.tsv';cmd=[str(ROOT/'results/tool-audit/runtime/bin/nextflow'),'-C',str(config),'run',str(ROOT/workflow),'-params-file',str(pf),'-work-dir',str(folder/'work'),'-with-trace',str(trace),'-ansi-log','false']+(['-preview'] if preview else [])
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=180);(folder/'stdout').write_text(result.stdout);(folder/'stderr').write_text(result.stderr)
        tasks=list(csv.DictReader(trace.open(),delimiter='\t')) if trace.exists() else []
        checks=dict(expected_exit=result.returncode==0 if preview else result.returncode!=0,diagnostic=preview or diagnostic in result.stdout+result.stderr,zero_tasks=not tasks,zero_commands=not list((folder/'work').rglob('.command.sh')))
        return dict(case=name,command=cmd,exit_code=result.returncode,preview_only=preview,checks=checks)

    with ThreadPoolExecutor(max_workers=2) as pool:runs=list(pool.map(execute,cases))
    row=dict(id='A.1',group='kept',fasta=str(assembly),bundle=str(base),reads=[str(data),str(r2)])
    shared=dict(platform='illumina',short_read_assembler='metaspades',plasmid_binning_tools=['plasmaag'],plasmaag_source=str(args.source.resolve()),genomad_db=str(base))
    negative=[('cohort-missing-reads',[dict(row,reads=[])],'Join mismatch'),('cohort-duplicate',[row,row],'Detected join operation duplicate emission'),
              ('cohort-read-meta',[dict(row,read_group='foreign')],'PlasMAAG read/assembly metadata differ for A.1'),('cohort-missing-bundle',[dict(row,bundle=None)],'Join mismatch'),
              ('cohort-bundle-meta',[dict(row,bundle_group='foreign')],'PlasMAAG SPAdes bundle metadata differ for A.1'),('cohort-empty',[],'PlasMAAG cohort is empty')]
    with ThreadPoolExecutor(max_workers=2) as pool:runs+=list(pool.map(lambda item:execute((item[0],dict(shared,records=item[1]),item[2],False),'tests/nextflow/plasmaag_workflow.nf',True),negative))
    result=dict(runs=runs,source_sha256=hashes,source_unchanged=hashes=={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in hashes},scope='8 main-entry rejections+2 parser previews and6 actual cohort integrity rejections; zero native analysis tasks, not biological validation')
    result['pass']=result['source_unchanged'] and all(all(r['checks'].values()) for r in runs);(base/'run.json').write_text(json.dumps(result,indent=2)+'\n');return 0 if result['pass'] else 1


if __name__=='__main__':raise SystemExit(main())
