#!/usr/bin/env python3
"""Full original ABRicate fixture: production runtime identity and cache controls."""
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


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def records(p):
    return list(csv.DictReader(p.open(), delimiter='\t'))


def run(base, prefix, fixture, golden):
    base.mkdir(parents=True, exist_ok=False)
    private = base / 'private'
    (private / 'bin').mkdir(parents=True)
    shutil.copy2(prefix / 'bin/abricate', private / 'bin/abricate')
    for name in ['ncbi', 'plasmidfinder']:
        shutil.copytree(prefix / 'db' / name, private / 'db' / name)
    alias = private / 'db/alias'
    alias.mkdir()
    subprocess.run([str(prefix / 'bin/blastdb_aliastool'), '-dblist', str(private / 'db/ncbi/sequences'),
                    '-dbtype', 'nucl', '-out', str(alias / 'sequences'), '-title', 'original full ncbi alias'], check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    watched = [private / 'bin/abricate', *sorted((private / 'db/ncbi').iterdir()),
               *sorted((private / 'db/plasmidfinder').iterdir())]
    originals = {p: (p.read_bytes(), p.stat()) for p in watched}
    for p in watched:
        original = prefix / p.relative_to(private)
        assert sha(p) == sha(original)
        assert (p.stat().st_dev, p.stat().st_ino) != (original.stat().st_dev, original.stat().st_ino)
    header = private / 'db/ncbi/sequences.nhr'
    original = header.read_bytes()
    target = b'penicillinase repressor BlaI'
    assert original.count(target) == 1
    changed = original.replace(target, b'Penicillinase repressor BlaI')
    assert len(original) == len(changed)
    sources = ['tests/run_abricate_runtime_native.py', 'tests/nextflow/abricate_runtime_native.nf',
               'bin/abricate_runtime_resources.pl', 'lib/abricate_runtime.nf',
               'modules/nf-core/abricate/run/main.nf', 'conf/nfcore_downstream.config']
    before = {p: sha(ROOT / p) for p in sources}
    env = dict(os.environ, PATH=str(private / 'bin') + ':' + str(prefix / 'bin') + ':' + os.environ['PATH'])
    params = dict(fasta=str(fixture), datadir=None, abricate_db='ncbi', outdir=str(base / 'out'), publish_dir_mode='copy')
    config = base / 'config'
    positive = "includeConfig '" + str(ROOT / 'conf/nfcore_downstream.config') + "'\nprocess { executor='local'; cpus=2; memory='2 GB'; errorStrategy='terminate'; maxRetries=0 }\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\ntrace.fields='task_id,hash,name,status,exit,workdir'\n"
    config.write_text(positive)
    expected = records(golden)
    assert len(expected) == 5
    runs = []
    session = None

    def execute(name, status, modified=False):
        nonlocal session
        case = base / name
        case.mkdir()
        (base / 'params.json').write_text(json.dumps(params))
        trace = case / 'trace.tsv'
        cmd = [str(ROOT / 'results/tool-audit/runtime/bin/nextflow'), '-C', str(config), 'run',
               str(ROOT / 'tests/nextflow/abricate_runtime_native.nf'), '-params-file', str(base / 'params.json'),
               '-work-dir', str(base / 'work'), '-with-trace', str(trace), '-ansi-log', 'false']
        cmd += ['-name', 'abricate_runtime_native'] if session is None else ['-resume', session]
        result = subprocess.run(cmd, cwd=base, env=env, capture_output=True, text=True, timeout=180)
        (case / 'stdout').write_text(result.stdout)
        (case / 'stderr').write_text(result.stderr)
        tasks = records(trace) if trace.exists() else []
        row = dict(case=name, command=cmd, exit_code=result.returncode, tasks=tasks,
                   private_header_sha256=sha(header) if header.exists() else None)
        runs.append(row)
        (base / 'progress.json').write_text(json.dumps(runs, indent=2) + '\n')
        if status in ['PROBE_FAILED', 'CONTEXT_REFUSED']:
            assert result.returncode != 0 and len(tasks) == 1, row
            assert tasks[0]['name'].startswith('ABRICATE_RESOURCE_PROBE'), row
            assert tasks[0]['status'] == ('FAILED' if status == 'PROBE_FAILED' else 'COMPLETED'), row
            if status == 'CONTEXT_REFUSED':
                assert 'runtime mismatch before cache lookup' in result.stdout + result.stderr
            row['no_consumer_submitted'] = True
        else:
            assert (result.returncode == 0) == (status != 'FAILED') and len(tasks) == 2, row
            probe = next(t for t in tasks if t['name'].startswith('ABRICATE_RESOURCE_PROBE'))
            consumer = next(t for t in tasks if t['name'].startswith('ABRICATE ('))
            assert probe['status'] == 'COMPLETED' and consumer['status'] == status, row
            if status == 'FAILED':
                assert result.returncode != 0
                assert 'ABRicate input converter/BLAST subprocess failed' in (Path(consumer['workdir']) / '.command.log').read_text()
                row['native_error_propagated'] = True
                print(name, status, flush=True)
                return
            identity_path = Path(probe['workdir']) / 'abricate_runtime_identity.json'
            identity = json.loads(identity_path.read_text())
            assert identity['resolved_locations']['datadir'] == str(private / 'db')
            assert identity['resolved_locations']['blast_volumes'] == [str(private / 'db/ncbi/sequences')]
            if params['abricate_db'] == 'alias':
                assert identity['resolved_locations']['selected_prefix'] == str(alias / 'sequences')
                row['external_alias_volume_recorded'] = True
            row.update(consumer_hash=consumer['hash'], identity_sha256=sha(identity_path))
            report = Path(consumer['workdir']) / ('sample.' + params['abricate_db'] + '.txt')
            observed = records(report)
            wanted = [dict(r) for r in expected]
            for r in wanted:
                r['#FILE'] = 'sample.' + params['abricate_db'] + '.fasta'
                if modified and r['PRODUCT'] == 'penicillinase repressor BlaI':
                    r['PRODUCT'] = 'Penicillinase repressor BlaI'
            assert observed == wanted, (name, observed, wanted)
            row.update(full_native_report_equal_expected=True, hits=len(observed), native_report_sha256=sha(report))
        if session is None:
            session = run_session_uuid('abricate_runtime_native', base)
        print(name, status, flush=True)

    def restore():
        for p, (data, st) in originals.items():
            p.write_bytes(data)
            p.chmod(st.st_mode & 0o7777)
            os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))

    def mutate():
        header.write_bytes(changed)
        st = originals[header][1]
        os.utime(header, ns=(st.st_atime_ns, st.st_mtime_ns))
        assert header.stat().st_size == st.st_size and header.stat().st_mtime_ns == st.st_mtime_ns

    try:
        execute('cold', 'COMPLETED')
        execute('unchanged', 'CACHED')
        mutate()
        execute('header-change', 'COMPLETED', True)
        restore()
        execute('header-restored', 'CACHED')
        params['datadir'] = str(private / 'db')
        execute('explicit-datadir', 'COMPLETED')
        execute('explicit-datadir-unchanged', 'CACHED')
        params['datadir'] = None
        params['abricate_db'] = 'alias'
        execute('alias-cold', 'COMPLETED')
        mutate()
        execute('external-alias-header-change', 'COMPLETED', True)
        restore()
        execute('external-alias-restored', 'CACHED')
        header.unlink()
        execute('external-alias-missing-header', 'FAILED')
    finally:
        restore()
    execute('all-restored', 'CACHED')
    for field, override in [('args', "ext.args='--db plasmidfinder'"), ('beforeScript', "beforeScript='export ABRICATE_CONTEXT_ONLY=1'")]:
        config.write_text(positive + "\nprocess { withName: 'ABRICATE' { " + override + " } }\n")
        execute('mismatch-' + field, 'CONTEXT_REFUSED')
    config.write_text(positive)
    assert runs[0]['consumer_hash'] == runs[1]['consumer_hash'] == runs[3]['consumer_hash']
    assert runs[6]['consumer_hash'] == runs[8]['consumer_hash'] == runs[10]['consumer_hash']
    for p in watched:
        actual = prefix / p.relative_to(private)
        assert sha(p) == sha(actual)
        assert (p.stat().st_mode & 0o7777) == (actual.stat().st_mode & 0o7777)
    assert before == {p: sha(ROOT / p) for p in sources}
    receipt = dict(pass_checks=True, runs=runs, session_uuid=session, source_sha256=before, source_unchanged=True,
                   resources_restored=True, original_resource_sha256={str(p.relative_to(private)):sha(p) for p in watched},
                   fixture_sha256=sha(fixture), native_original_report_sha256=sha(golden),
                   scope='Actual production ABRicate1.0.1+actual production config selector, full original2521797-byte fixture/full original5386 ncbi DB. Real header annotation equal-size/mtime change modifies precisely expected PRODUCT; restore/cache and external BLAST alias volume, explicit datadir, context controls. Native software-output baseline; no biological accuracy/full environment/OCI/provider/full-main certification.')
    (base / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('PASS: production ABRicate database resources/cache', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--golden', type=Path, required=True)
    args = parser.parse_args()
    run(args.out.resolve(), args.prefix.resolve(), args.fixture.resolve(), args.golden.resolve())
