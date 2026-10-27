#!/usr/bin/env python3
"""Full original PlasmidFinder2.1.6 positive: private native cache/resource controls."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from module_harness import run_session_uuid
from run_plasmidfinder_native import sequences

ROOT=Path(__file__).resolve().parents[1]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def run(base,prefix,upstream):
    base.mkdir(parents=True,exist_ok=False)
    source=prefix/'share/plasmidfinder-2.1.6/database';database=base/'private-database'
    shutil.copytree(source,database)
    bindir=base/'private-bin';bindir.mkdir();entry=bindir/'plasmidfinder.py'
    original=(prefix/'bin/plasmidfinder.py').read_text()
    relocated=re.sub(r'(?m)^PLASMIDFINDER_SHARE="[^"\n]+"$',lambda m:'PLASMIDFINDER_SHARE="'+str(database)+'"',original)
    assert relocated!=original and relocated.replace(str(database),str(source))==original
    entry.write_text(relocated);entry.chmod(0o755)
    watched=[p for p in database.rglob('*') if p.is_file()]
    originals={p:(p.read_bytes(),p.stat()) for p in watched}
    for p in watched:
        old=source/p.relative_to(database)
        assert sha(old)==sha(p) and (p.stat().st_dev,p.stat().st_ino)!=(old.stat().st_dev,old.stat().st_ino)
    fixture=upstream/'test/test.fsa';golden=(upstream/'test/test_results.tsv').read_text()
    assert fixture.stat().st_size==569 and list(map(len,sequences(fixture)))==[540]
    env=dict(os.environ,PATH=str(bindir)+':'+str(prefix/'bin')+':'+os.environ['PATH'],PYTHONDONTWRITEBYTECODE='1')
    config=base/'config'
    common="includeConfig '"+str(ROOT/'conf/nfcore_downstream.config')+"'\nparams.outdir='"+str(base/'out')+"'\nparams.publish_dir_mode='copy'\nprocess { executor='local';cpus=1;memory='1 GB';errorStrategy='terminate';maxRetries=0 }\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\ntrace.fields='task_id,hash,name,status,exit,workdir'\n"
    config.write_text(common)
    sources=['tests/run_plasmidfinder_runtime_native.py','tests/nextflow/plasmidfinder_native.nf','modules/nf-core/plasmidfinder/main.nf','modules/nf-core/plasmidfinder/environment.yml','lib/plasmidfinder_runtime.nf','bin/plasmidfinder_runtime_resources.py','conf/nfcore_downstream.config']
    before={p:sha(ROOT/p) for p in sources};runs=[];session=None
    def execute(name,status,note='R27',selected=False):
        nonlocal session
        case=base/name;case.mkdir();trace=case/'trace.tsv'
        cmd=[str(ROOT/'results/tool-audit/runtime/bin/nextflow'),'-C',str(config),'run',str(ROOT/'tests/nextflow/plasmidfinder_native.nf'),'--fasta',str(fixture),'-work-dir',str(base/'work'),'-with-trace',str(trace),'-ansi-log','false']
        cmd+=['-name','plasmidfinder_runtime_native'] if session is None else ['-resume',session]
        proc=subprocess.run(cmd,cwd=base,env=env,capture_output=True,text=True,timeout=180)
        (case/'stdout').write_text(proc.stdout);(case/'stderr').write_text(proc.stderr)
        tasks=list(csv.DictReader(trace.open(),delimiter='\t'));record=dict(case=name,command=cmd,exit_code=proc.returncode,tasks=tasks);runs.append(record)
        (base/'progress.json').write_text(json.dumps(runs,indent=2)+'\n')
        probe=next(t for t in tasks if t['name'].startswith('PLASMIDFINDER_RESOURCE_PROBE'))
        if status=='PROBE_FAILED':
            assert probe['status']=='FAILED' and len(tasks)==1 and proc.returncode!=0,record
            assert 'database file' in (Path(probe['workdir'])/'.command.log').read_text()
            record['no_consumer_submitted']=True
            print(name,status,flush=True)
            return
        assert probe['status']=='COMPLETED',record
        identity=Path(probe['workdir'])/'plasmidfinder_runtime_identity.json';resolved=json.loads(identity.read_text())
        assert resolved['resolved_locations']['database']==str(database)
        assert resolved['resolved_locations']['entrypoint']==str(entry)
        assert resolved['selected_databases']==(['enterobacteriaceae'] if selected else ['enterobacteriaceae','Inc18','NT_Rep','Rep1','Rep2','Rep3','RepA_N','RepL','Rep_trans'])
        record['identity_sha256']=sha(identity)
        if status=='CONTEXT_REFUSED':
            assert proc.returncode!=0 and len(tasks)==1,record
            assert 'runtime mismatch before cache lookup' in proc.stdout+proc.stderr
            record['no_consumer_submitted']=True
        else:
            consumer=next(t for t in tasks if t['name'].startswith('PLASMIDFINDER ('))
            assert len(tasks)==2 and consumer['status']==status,record
            assert (proc.returncode==0)==(status!='FAILED'),record
            record['consumer_hash']=consumer['hash'];work=Path(consumer['workdir'])
            if status=='FAILED':
                assert 'BLAST did not run as expected' in (work/'.command.log').read_text()
            else:
                report=work/'positive.plasmidfinder.tsv'
                assert report.read_text()==golden.replace('\tR27\t','\t'+note+'\t')
                for suffix in ['-hit_in_genome_seq.fsa','-plasmid_seqs.fsa']:
                    assert sequences(work/('positive.plasmidfinder'+suffix))==sequences(fixture)
                data=json.loads((work/'positive.plasmidfinder.json').read_text())['plasmidfinder']
                hit=next(iter(data['results']['Enterobacteriaceae']['enterobacteriaceae'].values()))
                assert hit['identity']==hit['coverage']==100 and hit['note']==note
                assert hit['HSP_length']==hit['template_length']==540 and hit['positions_in_contig']=='1..540'
                assert ('Gram Positive' not in data['results']) if selected else len(data['results']['Gram Positive'])==8
                record.update(full_original_golden_tsv_equal_except_expected_note=True,full_hit_and_reference_dna_equal=True)
        if session is None:session=run_session_uuid('plasmidfinder_runtime_native',base)
        print(name,status,flush=True)
    def restore():
        for p,(data,st) in originals.items():
            p.write_bytes(data);p.chmod(st.st_mode&0o7777);os.utime(p,ns=(st.st_atime_ns,st.st_mtime_ns))
    def mutate(p,data):
        st=originals[p][1];assert len(data)==st.st_size;p.write_bytes(data);os.utime(p,ns=(st.st_atime_ns,st.st_mtime_ns));assert p.stat().st_size==st.st_size and p.stat().st_mtime_ns==st.st_mtime_ns
    try:
        execute('cold','COMPLETED');execute('unchanged','CACHED')
        p=database/'enterobacteriaceae.fsa';data=originals[p][0];assert b'IncHI1B(R27)_1_R27_AF250878' in data
        mutate(p,data.replace(b'IncHI1B(R27)_1_R27_AF250878',b'IncHI1B(R27)_1_R28_AF250878',1));execute('same-stat-note','COMPLETED',note='R28');restore();execute('note-restored','CACHED')
        sidecar=database/'enterobacteriaceae.comp.b';data=bytearray(originals[sidecar][0]);data[-1]^=1;mutate(sidecar,bytes(data));execute('unused-kma-sidecar','COMPLETED');restore();execute('sidecar-restored','CACHED')
        p.unlink();execute('missing-selected-fsa','PROBE_FAILED');restore()
        mutate(p,b'X'*len(originals[p][0]));execute('corrupt-selected-fsa','FAILED');restore();execute('fsa-restored','CACHED')
        config.write_text(common+"process { withName: 'PLASMIDFINDER|PLASMIDFINDER_RESOURCE_PROBE' { ext.args='-d enterobacteriaceae -q' } }\n");execute('selected-quiet','COMPLETED',selected=True)
        for label,option in [('args',"ext.args='-d enterobacteriaceae'"),('before-script',"beforeScript='true'")]:
            config.write_text(common+"process { withName: 'PLASMIDFINDER' { "+option+" } }\n");execute('mismatched-'+label,'CONTEXT_REFUSED')
        config.write_text(common);execute('final-restored','CACHED')
    finally:restore()
    assert all(sha(p)==sha(source/p.relative_to(database)) and (p.stat().st_mode&0o7777)==(st.st_mode&0o7777) for p,(_,st) in originals.items())
    assert before=={p:sha(ROOT/p) for p in sources}
    result=dict(pass_bounded_checks=True,formal_acceptance=False,source_sha256=before,runs=runs,private_database_files_restored=len(originals),private_entrypoint_packaging_only_relocation=True,full_original_fixture_sha256=sha(fixture),scope='Actual fixed2.1.6 CLI/CGEcore/BLAST and complete upstream software positive; complete private packaged DB. Scientific header-note mutation, conservative unused KMA sidecar invalidation, restoration caches, real missing FSA failure, native taxonomy/quiet selection, pre-cache context refusal. No all-environment/OCI/scientific accuracy certificate.')
    (base/'run.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--prefix',type=Path,required=True);p.add_argument('--upstream',type=Path,required=True);a=p.parse_args();run(a.output.resolve(),a.prefix.resolve(),a.upstream.resolve())
