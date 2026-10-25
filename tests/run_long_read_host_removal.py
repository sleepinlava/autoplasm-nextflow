#!/usr/bin/env python3
"""Real mapper/SAMtools retention oracle and actual frozen-caller counterexample.

Synthetic exact reads have distinct host references and independently specified
origin/quality. This verifies wiring, not wet-lab host removal sensitivity.
"""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_workflow(directory, platform, before):
    source = (before / f'subworkflows/{platform}.nf').read_text()
    start = source.index('    ch_hr = ')
    end = source.index('\n', source.index('    ch_final_long = ', start))
    fragment = source[start:end].replace('FILTLONG.out.reads', 'ch_reads').replace('ch_hifi_reads', 'ch_reads')
    includes = [f"include {{ reportEvidence }} from '{ROOT}/lib/report_events'",
                f"include {{ MINIMAP2_ALIGN as MINIMAP2_ALIGN_HOST }} from '{before}/modules/nf-core/minimap2/align/main'",
                f"include {{ SAMTOOLS_VIEW as SAMTOOLS_VIEW_HOST }} from '{ROOT}/modules/nf-core/samtools/view/main'",
                f"include {{ SAMTOOLS_FASTQ as SAMTOOLS_FASTQ_HOST }} from '{ROOT}/modules/nf-core/samtools/fastq/main'"]
    module = directory / 'frozen_host.nf'
    module.write_text('\n'.join(includes) + '\nworkflow LONG_READ_HOST_REMOVAL {\n    take:\n    ch_reads\n    preset\n    main:\n    ch_report_events = Channel.empty()\n' + fragment + '\n    emit:\n    reads = ch_final_long\n    report_events = ch_report_events\n}\n')
    workflow = directory / 'probe.nf'
    workflow.write_text((ROOT / 'tests/nextflow/long_read_host_removal.nf').read_text().replace("'../../subworkflows/long_read_host_removal'", repr(str(module.with_suffix('')))))
    return workflow


def run(base, minimap, samtools, before):
    fixture = base / 'fixtures'
    fixture.mkdir()
    rng = random.Random(33020261022)
    sequences = {name: ''.join(rng.choices('ACGT', k=20000)) for name in ['A', 'B', 'P']}
    rc = lambda dna: dna.translate(str.maketrans('ACGT','TGCA'))[::-1]
    for name in ['A','B']:
        (fixture / f'host {name}.fasta').write_text('>host_' + name + '\n' + sequences[name] + '\n')
    reads = {'hostA': sequences['A'][1000:3000], 'hostA_reverse':rc(sequences['A'][5000:7000]),
             'hostB': sequences['B'][2000:4000], 'nonhost':sequences['P'][3000:5000],
             'nonhost_reverse':rc(sequences['P'][7000:9000])}
    expected = {}
    for sid in ['A','B','C','Z']:
        records = {sid+'_'+name:[dna,''.join(chr(53+(j+i)%31) for j in range(len(dna)))] for i,(name,dna) in enumerate(reads.items())}
        expected[sid] = records if sid == 'C' else {name:val for name,val in records.items() if not name.startswith(sid+'_host'+sid)}
        if sid == 'Z':
            records = {f'Z_{i}':[sequences['A'][1000+i*250:3000+i*250], 'I'*2000] for i in range(5)}
            expected[sid] = {}
        with gzip.open(fixture / f'{sid} input.fastq.gz','wt') as stream:
            stream.write(''.join('@'+name+'\n'+dna+'\n+\n'+quality+'\n' for name,(dna,quality) in records.items()))
    (base / 'origin-oracle.json').write_text(json.dumps({'expected':expected,'note':'exact, explicitly synthetic independent source/quality oracle; A and B have different host references, C bypasses'},indent=2)+'\n')
    hashes = {p.name:sha(p) for p in fixture.iterdir()}
    shim = base / 'fault-bin'
    shim.mkdir()
    binary = shim / 'minimap2'
    binary.write_text('#!/usr/bin/env python3\nimport subprocess,sys\nargs=sys.argv[1:]\nresult=subprocess.run(['+repr(str(minimap/'bin/minimap2'))+']+args)\nif args==["--version"]:raise SystemExit(result.returncode)\nprint("deliberate-post-mapping-failure",file=sys.stderr)\nraise SystemExit(result.returncode or 7)\n')
    binary.chmod(0o755)
    sources=['subworkflows/long_read_host_removal.nf','modules/nf-core/minimap2/align/main.nf',
             'modules/nf-core/samtools/view/main.nf','modules/nf-core/samtools/fastq/main.nf',
             'tests/run_long_read_host_removal.py','tests/nextflow/long_read_host_removal.nf']
    source_hashes={n:sha(ROOT/n) for n in sources}
    cases=[('before-'+name, 'map-hifi' if name=='pacbio_hifi' else 'map-ont',name,'mixed',False) for name in ['ont','pacbio_hifi','hybrid']]
    cases += [('before-fault','map-ont','ont','fault',True),('ont','map-ont',None,'mixed',False),
              ('hifi','map-hifi',None,'mixed',False),('depleted','map-ont',None,'depleted',False),('failed-mapper','map-ont',None,'fault',True)]
    runs=[]
    for name,preset,old_platform,kind,fault in cases:
        p=base/name;p.mkdir()
        workflow=frozen_workflow(p,old_platform,before) if old_platform else ROOT/'tests/nextflow/long_read_host_removal.nf'
        config=p/'native.config'
        mapper_path=str(shim)+':'+str(minimap/'bin') if fault else str(minimap/'bin')
        config.write_text(f"params.outdir='{p}/out'\nparams.publish_dir_mode='copy'\nincludeConfig '{ROOT}/conf/nfcore_upstream.config'\n"
            "process.executor='local'\nprocess.cpus=1\nprocess.memory='1 GB'\nprocess.maxForks=1\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\n"
            "process {\n"+f"withName:'MINIMAP2_ALIGN_HOST' {{ beforeScript='export PATH=\"{mapper_path}:$PATH\"' }}\n"
            +f"withName:'SAMTOOLS_VIEW_HOST|SAMTOOLS_FASTQ_HOST' {{ beforeScript='export PATH=\"{samtools}/bin:$PATH\"' }}\n}}\n"
            "trace.fields='task_id,hash,name,status,exit,workdir'\n")
        params={'fixture_dir':str(fixture),'fixture_case':'mixed' if kind=='mixed' else 'single','preset':preset}
        (p/'params.json').write_text(json.dumps(params))
        cmd=[shutil.which('nextflow') or 'nextflow','-C',str(config),'run',str(workflow),'-params-file',str(p/'params.json'),
             '-work-dir',str(p/'work'),'-with-trace',str(p/'trace.tsv'),'-ansi-log','false']
        result=subprocess.run(cmd,text=True,capture_output=True)
        (p/'stdout.log').write_text(result.stdout);(p/'stderr.log').write_text(result.stderr)
        tasks=list(csv.DictReader((p/'trace.tsv').open(),delimiter='\t')) if (p/'trace.tsv').exists() else []
        if old_platform:
            assert result.returncode==0,result.stdout+result.stderr
            if fault:
                assert next(t for t in tasks if 'MINIMAP2_ALIGN_HOST' in t['name'])['exit']=='0'
                assert 'deliberate-post-mapping-failure' in ''.join(q.read_text() for q in (p/'work').rglob('.command.err'))
            else:
                observed={json.loads(q.read_text())['meta']['id']:json.loads(q.read_text()) for q in (p/'work').rglob('*.observed.json')}
                assert not observed['A']['records'] and not observed['B']['records']
                assert observed['C']['records']==expected['C']
        elif kind=='mixed':
            assert result.returncode==0,result.stdout+result.stderr
            assert len(tasks)==9 and all(t['status']=='COMPLETED' and t['exit']=='0' for t in tasks)
            observed={json.loads(q.read_text())['meta']['id']:json.loads(q.read_text()) for q in (p/'work').rglob('*.observed.json')}
            assert set(observed)=={'A','B','C'}
            for sid in observed:
                assert observed[sid]['records']==expected[sid],(sid,observed[sid]['records'].keys(),expected[sid].keys())
                assert observed[sid]['meta']['group']=='preserved_group' and 'preset' not in observed[sid]['meta']
        else:
            assert result.returncode!=0
            assert not any('OBSERVE_LONG_READS' in t['name'] for t in tasks)
            if fault:
                assert next(t for t in tasks if 'MINIMAP2_ALIGN_HOST' in t['name'])['exit']=='7'
                assert not list((p/'out').rglob('*.bam'))
            else: assert 'No non-host long reads remain for sample Z' in result.stdout+result.stderr
        assert hashes=={q.name:sha(q) for q in fixture.iterdir()}
        assert source_hashes=={n:sha(ROOT/n) for n in sources}
        runs.append({'case':name,'command':cmd,'exit':result.returncode,'tasks':tasks,'old_caller_fragment':old_platform,
                     'checks':'known read IDs/DNA/quality retained, metadata/bypass preserved; category0 not stdout; fully depleted explicit QC failure; upstream pipeline failure not masked'})
        (base/'run.json').write_text(json.dumps({'runs':runs,'expected_cases':len(cases),'pass':len(runs)==len(cases),'source_sha256':source_hashes,'fixture_sha256':hashes,
            'limitations':['before harness is an exact frozen caller host-removal fragment with upstream read channel renamed, not a full old platform run',
                           'real minimap2/SAMtools on independent synthetic exact reads; not wet-lab host-removal performance',
                           'fault wrapper delegates real mapper then deliberately exits7; tests shell failure propagation, not a claim that the native mapper crashed',
                           'local native only; image/nf-test/full biological platform certification separate']},indent=2)+'\n')
        print('PASS',name,len(tasks),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir',required=True,type=Path)
    parser.add_argument('--minimap-prefix',required=True,type=Path)
    parser.add_argument('--samtools-prefix',required=True,type=Path)
    parser.add_argument('--before-dir',required=True,type=Path)
    args=parser.parse_args();base=args.work_dir.resolve();base.mkdir(parents=True,exist_ok=True)
    run(base,args.minimap_prefix.resolve(),args.samtools_prefix.resolve(),args.before_dir.resolve())
