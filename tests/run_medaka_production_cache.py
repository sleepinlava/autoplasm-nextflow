#!/usr/bin/env python3
"""Full-input production Medaka cache, corruption and compression controls.

Only private fixture copies are modified. All attempts and original native
software reference are retained; no input reduction or snapshot update.
"""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fasta(path, compressed=False):
    opener = gzip.open if compressed else open
    records = {}
    with opener(path, 'rt') as stream:
        header = None
        for line in stream:
            if line.startswith('>'):
                header = line.rstrip()
                assert header not in records
                records[header] = ''
            else:
                assert header is not None
                records[header] += line.strip()
    assert records and all(records.values())
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-root', type=Path, required=True)
    parser.add_argument('--native-reference', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    base = args.output.resolve()
    base.mkdir(parents=True, exist_ok=False)
    fixture = args.fixture_root.resolve()
    native = args.native_reference.resolve()
    prefix = args.prefix.resolve()
    reference = json.loads((native / 'run.json').read_text())
    assert reference['pass_native_computation_checks']
    expected = native / 'native/consensus.fasta'
    assert sha(expected) == reference['consensus_fasta_sha256']
    expected_records = fasta(expected)
    reads = fixture / 'sample_1_1/sample_1_1.filtered.fastq.gz'
    review = json.loads((native / 'input-review.json').read_text())
    assert sha(reads) == review['reads_sha256']
    original_draft = native / 'published-same-sample-draft.fasta'
    assert sha(original_draft) == review['draft_sha256']
    original_model = Path(json.loads((native / 'selection.json').read_text())['selected_model']['resolved_path'])
    source_files = ['modules/nf-core/medaka/main.nf', 'modules/nf-core/medaka/environment.yml',
                    'lib/medaka_runtime.nf', 'subworkflows/ont.nf', 'conf/nfcore_qc_assembly.config',
                    'tests/nextflow/medaka_runtime_resources.nf', 'tests/run_medaka_production_cache.py']
    source_files += ['bin/' + name for name in ['medaka_runtime_resources.py','medaka_model_resources.py',
                                               'medaka_model_selection.py','medaka_index_resources.py']]
    sources = {p: sha(root / p) for p in source_files}
    originals = {str(p): sha(p) for p in [original_model, original_draft,
                 Path(str(original_draft) + '.fai'), Path(str(original_draft) + '.map-ont.mmi')]}
    private = base / 'fixture'
    private.mkdir()
    draft = private / 'draft.fasta'
    for suffix in ['', '.fai', '.map-ont.mmi']:
        shutil.copy2(Path(str(original_draft) + suffix), Path(str(draft) + suffix))
    model = private / original_model.name
    shutil.copy2(original_model, model)
    ordinary_gzip = private / 'draft.fasta.gz'
    with ordinary_gzip.open('wb') as stream:
        subprocess.run(['gzip','-c',str(draft)],stdout=stream,check=True)
    bgzf = private / 'published-bgzf.fasta.gz'
    shutil.copy2(fixture / 'sample_1_1/sample_1_1.medaka.fasta.gz', bgzf)
    assert gzip.decompress(ordinary_gzip.read_bytes()) == draft.read_bytes()
    assert gzip.decompress(bgzf.read_bytes()) == draft.read_bytes()
    env = dict(os.environ, PATH=str(prefix / 'bin') + ':' + os.environ['PATH'],
               PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', CUDA_VISIBLE_DEVICES='')
    command_base = [str(root / 'results/tool-audit/20261026-plasmidfinder-runtime/nextflow-no-log')]
    runs = []

    def status(**data):
        (base / 'state.json').write_text(json.dumps(data, indent=2) + '\n')

    def run(name, expected_status, source=draft, mismatch=False):
        assert sources == {p: sha(root / p) for p in source_files}, 'Production source changed during queued validation'
        attempt = base / name
        attempt.mkdir(exist_ok=False)
        config = attempt / 'native.config'
        text = "process.executor='local'\nprocess.cpus=4\nprocess.memory='10 GB'\nprocess.maxForks=1\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\n"
        text += 'process.ext.args=' + json.dumps('-m ' + shlex.quote(str(model))) + '\n'
        text += "trace.fields=['task_id','hash','name','status','exit','workdir']\n"
        if mismatch:
            text += "process { withName: 'MEDAKA' { beforeScript='true' } }\n"
        config.write_text(text)
        command = command_base + ['-C',str(config),'-log',str(attempt / 'nextflow.log'),'run',
                   str(root / 'tests/nextflow/medaka_runtime_resources.nf'),
                   '--medaka_reads',str(reads),'--medaka_assembly',str(source),'--probe_only','false',
                   '-work-dir',str(base / 'work'),'-with-trace',str(attempt / 'trace.tsv')]
        if runs:
            command += ['-resume']
        (attempt / 'command.json').write_text(json.dumps(command,indent=2) + '\n')
        status(state='running', phase=name, command=command)
        print('Starting ' + name,flush=True)
        with (attempt / 'stdout').open('w') as stdout,(attempt / 'stderr').open('w') as stderr:
            result = subprocess.run(command,cwd=base,env=env,stdout=stdout,stderr=stderr)
        record = {'phase':name,'returncode':result.returncode,'command':command}
        (attempt / 'exit.json').write_text(json.dumps(record,indent=2) + '\n')
        trace = list(csv.DictReader((attempt / 'trace.tsv').open(),delimiter='\t'))
        record['trace'] = trace
        consumers = [row for row in trace if row['name'].startswith('MEDAKA (')]
        probes = [row for row in trace if row['name'].startswith('MEDAKA_RESOURCE_PROBE (')]
        if expected_status in ['COMPLETED','CACHED']:
            assert result.returncode == 0 and len(consumers) == 1 and len(probes) == 1,record
            assert probes[0]['status'] == 'COMPLETED' and consumers[0]['status'] == expected_status,record
            output = Path(consumers[0]['workdir']) / 'test.fa.gz'
            assert fasta(output,True) == expected_records, 'Complete headers/DNA differ from original native software reference'
            record['complete_fasta_matches_native'] = True
        else:
            assert result.returncode != 0 and not consumers,record
            if mismatch:
                assert 'runtime mismatch before cache lookup' in (attempt / 'nextflow.log').read_text()
            else:
                assert len(probes) == 1 and probes[0]['status'] == 'FAILED',record
        assert originals == {p: sha(Path(p)) for p in originals}, 'Original resource changed'
        runs.append(record)
        (attempt / 'run.json').write_text(json.dumps(record,indent=2) + '\n')
        status(state='phase_complete',phase=name,returncode=result.returncode)
        print(name + ': verified ' + expected_status,flush=True)

    def mutate(path, operation, phase, expected_status):
        original = path.read_bytes()
        st = path.stat()
        changed = operation(bytearray(original))
        assert len(changed) == len(original) and bytes(changed) != original
        path.write_bytes(changed)
        os.utime(path,ns=(st.st_atime_ns,st.st_mtime_ns))
        assert path.stat().st_size == st.st_size and path.stat().st_mtime_ns == st.st_mtime_ns
        try:
            run(phase,expected_status)
        finally:
            path.write_bytes(original)
            os.utime(path,ns=(st.st_atime_ns,st.st_mtime_ns))
        run(phase + '-restored','CACHED')

    def flip_at(index):
        def change(data):
            data[index] ^= 1
            return data
        return change

    run('baseline','COMPLETED')
    run('unchanged','CACHED')
    # A gzip header mtime byte changes full archive identity without changing
    # its exact decompressed TAR/model weights. This is a valid native model.
    header_change = flip_at(4)
    assert gzip.decompress(header_change(bytearray(model.read_bytes()))) == gzip.decompress(model.read_bytes())
    mutate(model,header_change,'valid-model-content-change','COMPLETED')
    mutate(model,flip_at(-1),'bad-model-trailer','FAILED')
    mutate(Path(str(draft) + '.map-ont.mmi'),flip_at(0),'bad-mmi-magic','FAILED')
    mutate(Path(str(draft) + '.fai'),flip_at(0),'bad-fai','FAILED')
    run('runtime-mismatch','FAILED',mismatch=True)
    run('runtime-restored','CACHED')
    run('ordinary-gzip','COMPLETED',source=ordinary_gzip)
    run('bgzf','COMPLETED',source=bgzf)
    assert sources == {p: sha(root / p) for p in source_files}
    report = {'pass_bounded_production_checks':True,'formal_acceptance':False,
              'source_sha256':sources,'original_resources_sha256':originals,'runs':runs,
              'scope':'Actual production probe+consumer, fixed full real bacterial reads/draft/model, complete native software-reference identity; private model/index same-size/mtime mutation and restore, pre-cache runtime mismatch, plain/gzip/BGZF. No biological genome accuracy, all optional RLE/force/regions or OCI/platform acceptance.'}
    (base / 'run.json').write_text(json.dumps(report,indent=2) + '\n')
    status(state='terminal',returncode=0,phases=len(runs))


if __name__ == '__main__':
    main()
