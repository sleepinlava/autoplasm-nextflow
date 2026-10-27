#!/usr/bin/env python3
"""Production SemiBin runtime-resource identities and pre-cache context guards."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from module_harness import run_session_uuid
from run_semibin_states import dna

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(base, prefix, fixture):
    base.mkdir(parents=True, exist_ok=False)
    package = prefix / 'lib/python3.12/site-packages/SemiBin'
    private = base / 'private-python/SemiBin'
    shutil.copytree(package, private, ignore=shutil.ignore_patterns('__pycache__'))
    marker = private / 'marker.hmm'
    original = marker.read_bytes()
    original_stat = marker.stat()
    original_sha = sha(package / 'marker.hmm')
    module = ROOT / 'modules/nf-core/semibin/singleeasybin/main.nf'
    workflow = ROOT / 'tests/nextflow/semibin_runtime_native.nf'
    params = dict(probe=str(ROOT / 'tests/semibin_runtime_resource_probe.py'),
                  fasta=str(fixture / 'input.fasta'), bam=str(fixture / 'input.sorted.bam'),
                  state_helper=str(ROOT / 'bin/semibin_output_state.py'))
    (base / 'params.json').write_text(json.dumps(params))
    config = base / 'config'
    config.write_text("process { executor='local'; cpus=2; memory='2 GB'; errorStrategy='terminate'; maxRetries=0; withName: 'SEMIBIN|SEMIBIN_RESOURCE_PROBE' { ext.args2='--random-seed 0' } }\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\ntrace.fields='task_id,hash,name,status,exit,workdir'\n")
    env = dict(os.environ, PATH=str(prefix / 'bin') + ':' + os.environ['PATH'],
               PYTHONPATH=str(private.parent), OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2',
               MKL_NUM_THREADS='2', PYTHONDONTWRITEBYTECODE='1')
    source = dna(fixture / 'input.fasta')
    assert len(source) == 40 and sum(map(len, source.values())) == 800000
    sources = ['tests/run_semibin_runtime_native.py', 'bin/semibin_runtime_resources.py',
               'lib/semibin_runtime.nf', 'tests/nextflow/semibin_runtime_native.nf', str(module.relative_to(ROOT)),
               'bin/semibin_output_state.py']
    before = {p: sha(ROOT / p) for p in sources}
    runs = []
    session = None

    def execute(name, expected):
        nonlocal session
        case = base / name
        case.mkdir()
        trace = case / 'trace.tsv'
        cmd = [str(ROOT / 'results/tool-audit/runtime/bin/nextflow'), '-C', str(config),
               'run', str(workflow), '-params-file', str(base / 'params.json'),
               '-work-dir', str(base / 'work'), '-with-trace', str(trace), '-ansi-log', 'false']
        if session is None:
            cmd += ['-name', 'semibin_runtime_native']
        else:
            cmd += ['-resume', session]
        result = subprocess.run(cmd, cwd=base, env=env, text=True, capture_output=True, timeout=600)
        (case / 'stdout').write_text(result.stdout)
        (case / 'stderr').write_text(result.stderr)
        tasks = list(csv.DictReader(trace.open(), delimiter='\t')) if trace.exists() else []
        record = dict(case=name, command=cmd, exit_code=result.returncode, tasks=tasks,
                      private_marker_sha256=sha(marker))
        runs.append(record)
        (base / 'progress.json').write_text(json.dumps(runs, indent=2) + '\n')
        assert len(tasks) == 2, record
        probe = [t for t in tasks if t['name'].startswith('SEMIBIN_RESOURCE_PROBE')][0]
        task = [t for t in tasks if t['name'].startswith('SEMIBIN (')][0]
        assert probe['status'] == 'COMPLETED', record
        assert task['status'] == expected, record
        assert (result.returncode == 0) == (expected != 'FAILED'), record
        work = Path(task['workdir'])
        if expected == 'COMPLETED':
            out = work / 'sample'
            state = json.loads((out / 'binning_status.json').read_text())
            bins = list((out / 'output_bins').glob('*.fa.gz'))
            assert bins and state['state'] == 'bins_ready' and state['bin_count'] == len(bins)
            seen = set()
            for path in bins:
                seqs = dna(path)
                assert seqs and not seen.intersection(seqs)
                assert all(source[k] == seq for k, seq in seqs.items())
                seen.update(seqs)
            assert (out / 'model.pt').is_file()
            record['independent_DNA_and_state_checks'] = True
        if expected == 'FAILED':
            log = (work / '.command.log').read_text()
            assert 'hmmsearch' in log and ('format' in log.lower() or 'parse' in log.lower()), log[-3000:]
            assert 'Runtime marker differs' not in log
        if session is None:
            session = run_session_uuid('semibin_runtime_native', base)
        record['consumer_hash'] = task['hash']
        record['identity_sha256'] = sha(Path(probe['workdir']) / 'semibin_runtime_identity.json')
        print(name, expected, flush=True)

    def mutate(data):
        assert len(data) == len(original)
        marker.write_bytes(data)
        os.utime(marker, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
        assert marker.stat().st_size == original_stat.st_size
        assert marker.stat().st_mtime_ns == original_stat.st_mtime_ns

    try:
        execute('cold', 'COMPLETED')
        execute('unchanged', 'CACHED')
        # HMM description text is not a numerical parameter or profile state.
        changed = bytearray(original)
        desc = original.index(b'DESC  ') + len(b'DESC  ')
        changed[desc] = ord('X') if changed[desc] != ord('X') else ord('Y')
        mutate(bytes(changed))
        execute('description-change', 'COMPLETED')
        execute('changed-unchanged', 'CACHED')
        corrupt = bytearray(original)
        corrupt[0] = ord('X')
        mutate(bytes(corrupt))
        execute('corrupt-header', 'FAILED')
    finally:
        mutate(original)
    execute('restored', 'CACHED')
    positive_config = config.read_text()
    for field, override in [('args', "ext.args2='--random-seed 1'"),
                            ('container', "container='TEST_ONLY_DIFFERENT_CONTAINER'")]:
        config.write_text(positive_config + "\nprocess { withName: 'SEMIBIN' { " + override + " } }\n")
        case = base / ('mismatch-' + field)
        case.mkdir()
        trace = case / 'trace.tsv'
        cmd = [str(ROOT / 'results/tool-audit/runtime/bin/nextflow'), '-C', str(config),
               'run', str(workflow), '-params-file', str(base / 'params.json'),
               '-work-dir', str(base / 'work'), '-with-trace', str(trace),
               '-ansi-log', 'false', '-resume', session]
        result = subprocess.run(cmd,cwd=base,env=env,text=True,capture_output=True,timeout=120)
        (case/'stdout').write_text(result.stdout)
        (case/'stderr').write_text(result.stderr)
        tasks = list(csv.DictReader(trace.open(),delimiter='\t')) if trace.exists() else []
        assert result.returncode != 0 and 'runtime mismatch before cache lookup' in result.stdout+result.stderr, result.stdout+result.stderr
        assert len(tasks)==1 and tasks[0]['name'].startswith('SEMIBIN_RESOURCE_PROBE') and tasks[0]['status']=='COMPLETED', tasks
        runs.append(dict(case='mismatch-'+field,command=cmd,exit_code=result.returncode,tasks=tasks,
                         pre_cache_refusal=True,no_consumer_task_submitted=True))
        print('mismatch-'+field,'REFUSED_BEFORE_CACHE',flush=True)
    config.write_text(positive_config)
    assert runs[0]['consumer_hash'] == runs[1]['consumer_hash'] == runs[5]['consumer_hash']
    assert runs[2]['consumer_hash'] == runs[3]['consumer_hash'] != runs[0]['consumer_hash']
    assert sha(package / 'marker.hmm') == original_sha == sha(marker)
    assert before == {p: sha(ROOT / p) for p in sources}
    receipt = dict(pass_checks=True, runs=runs, session_uuid=session, source_sha256=before,
                   source_unchanged=True, original_marker_unchanged=True,
                   production_module_sha256=sha(module),
                   fixture_sha256={p: sha(fixture / p) for p in ['input.fasta', 'input.sorted.bam']},
                   scope='Actual production module and pre-cache/runtime guards; default SemiBin2.4.1 CPU15epochs, full official40contig800000bp fixture, seed0. Probe always runs before lookup. Conditional-resource parser tests separate; no OCI/GPU inference/platform or biological accuracy certification.')
    (base / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('PASS: production runtime probe/native consumer and context guards', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    args = parser.parse_args()
    run(args.out.resolve(), args.prefix.resolve(), args.fixture.resolve())
