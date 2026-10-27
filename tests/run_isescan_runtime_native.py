#!/usr/bin/env python3
"""Actual fixed ISEScan/FragGeneScan/SSW cache controls, never accuracy truth."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from module_harness import run_session_uuid

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ['isescan.py','constants.py','isPredict.py','is_analysis.py','pred.py','tools.py','ssw_wrap.py','pyssw.py']


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fasta(p):
    records = {}
    for line in p.read_text().splitlines():
        if line.startswith('>'):
            name = line[1:].split()[0]
            assert name not in records
            records[name] = ''
        elif line.strip():
            records[name] += line.strip()
    assert records and all(records.values())
    return records


def check_output(directory, input_fasta, golden):
    tsvs = list(directory.rglob('*.tsv'))
    assert len(tsvs) == 1, tsvs
    rows = list(csv.DictReader(tsvs[0].open(),delimiter='\t'))
    assert rows == list(csv.DictReader(golden.open(),delimiter='\t'))
    assert len(rows)==1 and rows[0]['family']=='IS5' and rows[0]['cluster']=='IS5_222'
    sequence = fasta(input_fasta)
    row = rows[0]
    selected = sequence[row['seqID']]
    begin,end = int(row['isBegin']),int(row['isEnd'])
    assert (begin,end,int(row['isLen']))==(30355,31343,989)
    actual = fasta(next(directory.rglob('*.is.fna')))
    assert len(actual)==1 and next(iter(actual.values()))==selected[begin-1:end]
    orf = fasta(next(directory.rglob('*.orf.fna')))
    assert len(orf)==1 and next(iter(orf.values()))==selected[int(row['orfBegin'])-1:int(row['orfEnd'])]
    assert row['strand']=='+' and len(next(iter(orf.values())))==900
    return dict(original_native_TSV_equal=True,independent_IS_and_ORF_DNA_equal=True,IS_count=1,IS_length=989)


def run(base,prefix,input_fasta,golden):
    base.mkdir(parents=True,exist_ok=False)
    private = base/'private-install'
    # A thin PATH/LD_LIBRARY_PATH overlay does not override every Conda RPATH.
    # Materialize the exact locked environment at its own prefix; always-copy
    # prevents model mutations from touching original/cache hard links.
    lock=base/'native.lock'
    packages=[json.loads(p.read_text()) for p in sorted((prefix/'conda-meta').glob('*.json'))]
    assert packages and all(p.get('url') and p.get('md5') for p in packages)
    lock.write_text('@EXPLICIT\n'+'\n'.join(p['url']+'#'+p['md5'] for p in packages)+'\n')
    command=['/home/sleepinlava/.local/bin/micromamba','--root-prefix',str(ROOT/'results/tool-audit/runtime/mamba-root'),
             'create','--prefix',str(private),'--file',str(lock),'--offline','--always-copy','--json','-y']
    with (base/'private-install.json').open('w') as out,(base/'private-install.stderr').open('w') as err:
        install=subprocess.run(command,stdout=out,stderr=err)
    assert install.returncode==0,install.returncode
    mutable=[private/'bin/pHMMs/clusters.faa.hmm',private/'bin/train/illumina_5',private/'lib/libssw.so']
    originals={p:p.read_bytes() for p in mutable}
    stats={p:p.stat() for p in mutable}
    watched=[private/'bin'/name for name in SCRIPTS+['FragGeneScan','run_FragGeneScan.pl']] + list((private/'bin/pHMMs').iterdir()) + list((private/'bin/train').iterdir()) + [private/'lib/libssw.so']
    original_package={str(p.relative_to(private)):sha(p) for p in watched if p.is_file()}
    for p in mutable:
        shared=prefix/p.relative_to(private)
        assert (p.stat().st_dev,p.stat().st_ino)!=(shared.stat().st_dev,shared.stat().st_ino),p
        assert sha(p)==sha(shared),p
    env=dict(os.environ,PATH=str(private/'bin')+':'+str(prefix/'bin')+':'+os.environ['PATH'],
             LD_LIBRARY_PATH=str(private/'lib')+':'+str(prefix/'lib'),PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='2',OMP_NUM_THREADS='2')
    config=base/'config'
    config.write_text("process { executor='local'; cpus=2; memory='2 GB'; errorStrategy='terminate'; maxRetries=0 }\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\nparams.publish_dir_mode='copy'\nparams.outdir="+repr(str(base/'out'))+"\ntrace.fields='task_id,hash,name,status,exit,workdir'\n")
    positive_config=config.read_text()
    (base/'params.json').write_text(json.dumps(dict(fasta=str(input_fasta))))
    sources=['modules/annotation/isescan.nf','lib/isescan_runtime.nf','bin/isescan_runtime_resources.py','envs/isescan.yml','tests/nextflow/isescan_runtime_native.nf','tests/run_isescan_runtime_native.py']
    before={p:sha(ROOT/p) for p in sources}
    runs=[]
    session=None

    def execute(name,expected):
        nonlocal session
        case=base/name;case.mkdir()
        cmd=[str(ROOT/'results/tool-audit/runtime/bin/nextflow'),'-C',str(config),'run',str(ROOT/'tests/nextflow/isescan_runtime_native.nf'),'-params-file',str(base/'params.json'),'-work-dir',str(base/'work'),'-with-trace',str(case/'trace.tsv'),'-ansi-log','false']
        cmd+=['-resume',session] if session else ['-name','isescan_runtime_native']
        result=subprocess.run(cmd,cwd=base,env=env,capture_output=True,text=True,timeout=600)
        (case/'stdout').write_text(result.stdout);(case/'stderr').write_text(result.stderr)
        tasks=list(csv.DictReader((case/'trace.tsv').open(),delimiter='\t')) if (case/'trace.tsv').exists() else []
        record=dict(case=name,command=cmd,exit_code=result.returncode,tasks=tasks,resource_sha256={str(p.relative_to(private)):sha(p) for p in mutable})
        runs.append(record);(base/'progress.json').write_text(json.dumps(runs,indent=2)+'\n')
        assert len(tasks)==2,record
        probe=next(t for t in tasks if t['name'].startswith('ISESCAN_RESOURCE_PROBE'))
        consumer=next(t for t in tasks if t['name'].startswith('ISESCAN ('))
        assert probe['status']=='COMPLETED' and consumer['status']==expected,record
        assert (result.returncode==0)==(expected!='FAILED'),record
        work=Path(consumer['workdir'])
        if expected=='COMPLETED':
            record['output_checks']=check_output(work/'S.1.isescan_out',input_fasta,golden)
            assert 'ISESCAN_RESULT=' in result.stdout and 'FIXED_SOFTWARE_FIXTURE' in result.stdout
        if expected=='FAILED':
            log=(work/'.command.log').read_text()
            assert 'hmmsearch' in log.lower() or 'format' in log.lower(),log[-2500:]
        record['consumer_hash']=consumer['hash']
        record['identity_sha256']=sha(Path(probe['workdir'])/'isescan_runtime_identity.json')
        if session is None:session=run_session_uuid('isescan_runtime_native',base)
        print(name,expected,flush=True)

    def set_bytes(p,data):
        assert len(data)==len(originals[p])
        p.write_bytes(data)
        os.utime(p,ns=(stats[p].st_atime_ns,stats[p].st_mtime_ns))
        assert p.stat().st_size==stats[p].st_size and p.stat().st_mtime_ns==stats[p].st_mtime_ns

    try:
        execute('cold','COMPLETED')
        execute('unchanged','CACHED')
        p=mutable[0];data=bytearray(originals[p]);i=originals[p].index(b'DATE  ');i=originals[p].index(b'2017',i)+3;data[i]=ord('8');set_bytes(p,bytes(data))
        execute('HMM-DATE-metadata-change','COMPLETED');set_bytes(p,originals[p]);execute('HMM-restored','CACHED')
        p=mutable[1];data=bytearray(originals[p]);i=originals[p].index(b'GG      ')+2;data[i]=ord('\t');set_bytes(p,bytes(data))
        execute('FGS-model-whitespace-change','COMPLETED');set_bytes(p,originals[p]);execute('FGS-restored','CACHED')
        p=mutable[2];data=bytearray(originals[p]);i=originals[p].index(b'GCC:');data[i+2]=ord('D');set_bytes(p,bytes(data))
        execute('SSW-nonalloc-comment-change','COMPLETED');set_bytes(p,originals[p]);execute('SSW-restored','CACHED')
        p=mutable[0];data=bytearray(originals[p]);data[0]=ord('X');set_bytes(p,bytes(data));execute('corrupt-HMM','FAILED')
    finally:
        for p,data in originals.items():set_bytes(p,data)
    execute('all-restored','CACHED')
    cold_hash=runs[0]['consumer_hash']
    assert all(runs[i]['consumer_hash']==cold_hash for i in [1,3,5,7,9])
    assert all(runs[i]['consumer_hash']!=cold_hash for i in [2,4,6,8])
    for name,override in [('container',"container='TEST_ONLY_OTHER_IMAGE'"),('beforeScript',"beforeScript='export TEST_ONLY_ISESCAN_CONTEXT=1'")]:
        case=base/('mismatch-'+name);case.mkdir();config.write_text(positive_config+"\nprocess { withName:'ISESCAN' { "+override+" } }\n")
        cmd=[str(ROOT/'results/tool-audit/runtime/bin/nextflow'),'-C',str(config),'run',str(ROOT/'tests/nextflow/isescan_runtime_native.nf'),'-params-file',str(base/'params.json'),'-work-dir',str(base/'work'),'-with-trace',str(case/'trace.tsv'),'-ansi-log','false','-resume',session]
        result=subprocess.run(cmd,cwd=base,env=env,capture_output=True,text=True,timeout=120)
        (case/'stdout').write_text(result.stdout);(case/'stderr').write_text(result.stderr)
        tasks=list(csv.DictReader((case/'trace.tsv').open(),delimiter='\t')) if (case/'trace.tsv').exists() else []
        assert result.returncode!=0 and 'runtime mismatch before cache lookup' in result.stdout+result.stderr
        assert len(tasks)==1 and tasks[0]['name'].startswith('ISESCAN_RESOURCE_PROBE') and tasks[0]['status']=='COMPLETED',tasks
        runs.append(dict(case='mismatch-'+name,command=cmd,exit_code=result.returncode,tasks=tasks,consumer_not_submitted=True))
        print('mismatch-'+name,'REFUSED_BEFORE_CACHE',flush=True)
    config.write_text(positive_config)
    assert before=={p:sha(ROOT/p) for p in sources}
    assert original_package=={str(p.relative_to(private)):sha(p) for p in watched if p.is_file()}
    receipt=dict(pass_checks=True,runs=runs,session_uuid=session,source_sha256=before,source_unchanged=True,private_package_restored=True,original_package_sha256=original_package,input_sha256=sha(input_fasta),golden_sha256=sha(golden),scope='Full always-copy independent locked environment; full original NC_012624 fixture/default1.7.3+FGS1.32 illumina_5; private same-size/mtime changes only DATE metadata/whitespace/nonallocated ELF comment, native HMM failure/restore/context guards. Exact native golden plus independent IS/ORF DNA; software contract, not biological accuracy, OCI/provider or full-pipeline certification.')
    (base/'run.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('PASS: ISEScan native runtime-resource controls',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['out','prefix','fasta','golden']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();run(args.out.resolve(),args.prefix.resolve(),args.fasta.resolve(),args.golden.resolve())
