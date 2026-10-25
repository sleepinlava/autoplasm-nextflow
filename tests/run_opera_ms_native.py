#!/usr/bin/env python3
"""Run the original OPERA-MS module with a fixed, real native installation."""
from module_harness import render_module_harness
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fasta(path):
    records = {}
    rid = None
    for line in path.read_text().splitlines():
        if line.startswith('>'):
            rid = line[1:].split()[0]
            assert rid and rid not in records
            records[rid] = ''
        else:
            assert rid is not None
            records[rid] += line.strip().upper()
    assert records and all(seq and re.fullmatch('[ACGTRYSWKMBDHVN]+',seq) for seq in records.values())
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir',type=Path,required=True)
    parser.add_argument('--native-env',type=Path,required=True)
    parser.add_argument('--opera-root',type=Path,required=True)
    parser.add_argument('--read1',type=Path,required=True)
    parser.add_argument('--read2',type=Path,required=True)
    parser.add_argument('--long-reads',type=Path,required=True)
    parser.add_argument('--module-source',type=Path)
    parser.add_argument('--sample-id',default='minigut_hybrid')
    parser.add_argument('--expect',choices=['success','gzip-rejected','gzip-corrupt','internal-fatal'],default='success')
    args = parser.parse_args()
    base = args.work_dir.resolve()
    base.mkdir(parents=True,exist_ok=False)
    env_script, install = args.native_env.resolve(),args.opera_root.resolve()
    program = install/'OPERA-MS.pl'
    data = program.read_bytes()
    assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()=='08c41900c791669dabd0755329d4fe615a7ca04a'
    module = args.module_source.resolve() if args.module_source else ROOT/'modules/assembly/opera_ms.nf'
    source_files = [module,ROOT/'tests/nextflow/opera_ms_native.nf',ROOT/'tests/run_opera_ms_native.py',env_script,program,
                    ROOT/'bin/validate_opera_ms_output.py']
    sources = {str(p):sha(p) for p in source_files}
    inputs = [p.resolve() for p in [args.read1,args.read2,args.long_reads]]
    input_sha = {str(p):sha(p) for p in inputs}
    params = {'outdir':str(base/'out'),'publish_dir_mode':'copy','sample_id':args.sample_id,
              **dict(zip(['read1','read2','long_reads'],map(str,inputs)))}
    pf = base/'params.json'
    pf.write_text(json.dumps(params))
    # The env wrapper executes arbitrary supplied command; use it as shell init
    # by sourcing a version without its final exec line for actual task execution.
    setup = env_script.read_text()
    assert setup.endswith('exec "$@"\n')
    init = base/'native-init.sh'
    # BASH_SOURCE would otherwise point to this private case directory.
    setup = re.sub(r'^audit_root=.*$', 'audit_root='+shlex.quote(str(ROOT)),setup,flags=re.M)
    init.write_text(setup.removesuffix('exec "$@"\n'))
    before_script = '. '+shlex.quote(str(init))
    literal = "'"+before_script.replace('\\','\\\\').replace("'","\\'")+"'"
    config = base/'native.config'
    config.write_text("process.executor='local'\nprocess.cpus=2\nprocess.memory='6 GB'\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\n"
                      "trace.fields='task_id,hash,name,status,exit,workdir'\nprocess.beforeScript="+literal+'\n')
    harness = ROOT/'tests/nextflow/opera_ms_native.nf'
    if args.module_source:
        private = base/'original-module.nf'
        private.write_text(render_module_harness(harness, '../../modules/assembly/opera_ms', module, 'validate_opera_ms_output.py'))
        harness = private
    command = [shutil.which('nextflow') or 'nextflow','-C',str(config),'run',str(harness),'-params-file',str(pf),
               '-work-dir',str(base/'work'),'-with-trace',str(base/'trace.tsv'),'-ansi-log','false']
    result = subprocess.run(command,cwd=base,capture_output=True,text=True)
    (base/'console.log').write_text(result.stdout+result.stderr)
    with (base/'trace.tsv').open() as stream:
        tasks=list(csv.DictReader(stream,delimiter='\t'))
    assert len(tasks)==1,tasks
    work=Path(tasks[0]['workdir'])
    error=(work/'.command.err').read_text()
    emitted=base/'out/02_assembly/opera_ms'/f'{args.sample_id}.opera_ms.contigs.fasta'
    details={}
    if args.expect!='success':
        assert result.returncode!=0 and tasks[0]['status']=='FAILED',result.stdout+result.stderr
        assert not emitted.exists()
        if args.expect=='gzip-rejected':
            assert 'does not accept compressed long read file' in error,error
        elif args.expect=='gzip-corrupt':
            assert 'gzip:' in error and ('unexpected end' in error or 'not in gzip format' in error),error
            assert not (work/f'{args.sample_id}.opera_ms_out').exists()
        else:
            assert 'OPERA-MS internal process failure' in error,error
            assert (work/f'{args.sample_id}.opera_ms_out/contigs.fasta').stat().st_size>0
    else:
        assert result.returncode==0 and tasks[0]['status']=='COMPLETED',result.stdout+result.stderr
        output=work/f'{args.sample_id}.opera_ms_out'
        final=output/'contigs.fasta'
        assert final.read_bytes()==emitted.read_bytes()
        records=fasta(emitted)
        lengths=sorted(map(len,records.values()),reverse=True)
        n50=next(length for i,length in enumerate(lengths) if sum(lengths[:i+1])*2>=sum(lengths))
        stats=(output/'assembly.stats').read_text()
        for label,value in [('Number of contigs',len(records)),('Assembly size',sum(lengths)),('Max contig size',max(lengths)),('Contig N50',n50)]:
            match=re.search(re.escape(label)+r':\s*(\d+)',stats)
            assert match and int(match.group(1))==value,(label,value,stats)
        candidates=[p for p in (output/'intermediate_files').rglob('*') if p.is_file() and p.suffix.lower() in ['.fa','.fasta']]
        details={'contigs':len(records),'bases':sum(lengths),'longest':max(lengths),'n50':n50,
                 'final_sha256':sha(final),'assembly_stats_sha256':sha(output/'assembly.stats'),
                 'intermediate_fasta_sha256':{str(p.relative_to(output)):sha(p) for p in candidates},
                 'config_sha256':{str(p.relative_to(output)):sha(p) for p in output.glob('*.config')}}
    assert input_sha=={str(p):sha(p) for p in inputs},'Input source changed'
    assert sources=={str(p):sha(p) for p in source_files},'Source changed during run'
    receipt={'pass':True,'expected':args.expect,'command':command,'exit':result.returncode,'tasks':tasks,
             'source_sha256':sources,'input_sha256':input_sha,'details':details,
             'stderr_sha256':sha(work/'.command.err'),
             'limitations':['Real fixed OPERA-MS0.8.3 with default module parameters; no external tool doubles',
                            'Exact final-product selection/input contract only; not scientific assembly-accuracy or full platform certification',
                            'Direct original-module Nextflow harness; not nf-test framework execution']}
    (base/'run.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('PASS',args.expect,json.dumps(details),flush=True)


if __name__=='__main__':
    main()
