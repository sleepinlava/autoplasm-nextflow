#!/usr/bin/env python3
"""Two-sample native IO and exact-session source-cache controls for gplas."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ['output', 'prefix', 'source', 'graph', 'predictions']:
        parser.add_argument('--' + flag, type=Path, required=True)
    args = parser.parse_args()
    base = args.output.resolve(); base.mkdir(exist_ok=False)
    source = base / 'private-source'; shutil.copytree(args.source.resolve(), source)
    fixture = base / 'fixture'; fixture.mkdir()
    variant = fixture / 'variant.gfa'
    # Explicit synthetic DNA transport counterfactual, supplied classifications:
    # no claim that the altered sequences are independent biological samples.
    lines = []
    for line in args.graph.read_text().splitlines():
        cells = line.split('\t')
        if cells[0] == 'S':
            cells[2] = cells[2].translate(str.maketrans('ACGTacgt', 'TGCAtgca'))
        lines.append('\t'.join(cells))
    variant.write_text('\n'.join(lines) + '\n')
    assert sha(variant) != sha(args.graph)
    ready = fixture / 'positive.ready'; ready.write_text('supplied native software IO fixture\n')
    records = [{'id': 'A.1', 'graph': str(args.graph.resolve()), 'predictions': str(args.predictions.resolve())},
               {'id': 'A__1', 'graph': str(variant), 'predictions': str(args.predictions.resolve())}]
    config = base / 'nextflow.config'
    config.write_text("process.executor='local'\nprocess.cpus=1\nprocess.memory='3 GB'\nprocess.maxForks=2\n"
                      "process.errorStrategy='terminate'\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\n"
                      "params.publish_dir_mode='copy'\ntrace.fields='task_id,hash,name,status,exit,workdir'\n")
    settings = {'records': records, 'gplas_source': str(source), 'ready_marker': str(ready), 'outdir': str(base / 'out')}
    params = base / 'params.json'
    files = ['bin/gplas_checked.py', 'modules/binning/gplas2.nf', 'envs/gplas2.yml',
             'tests/nextflow/gplas_native.nf', 'tests/check_gplas_native.py', 'tests/run_gplas_native.py']
    source_hash = {p: sha(ROOT / p) for p in files}
    original = source / 'gplas/version.py'; data = original.read_bytes(); stamp = original.stat()
    bad = data.replace(b'1.1.1.dev8', b'9.1.1.dev8')
    assert len(data) == len(bad) and data != bad
    runs, session = [], None
    name = 'gplas_' + hashlib.sha256(str(base).encode()).hexdigest()[:12]
    env = {**os.environ, 'PATH': str(args.prefix.resolve() / 'bin') + ':' + os.environ['PATH'],
           'PYTHONDONTWRITEBYTECODE': '1'}
    try:
        for phase in ['cold', 'resume', 'bad-source', 'restored-source']:
            original.write_bytes(bad if phase == 'bad-source' else data)
            os.utime(original, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
            options = dict(settings, outdir=str(base / ('bad-out' if phase == 'bad-source' else 'out')))
            params.write_text(json.dumps(options, indent=2) + '\n')
            trace = base / (phase + '.trace.tsv')
            cmd = [str(ROOT / 'results/tool-audit/runtime/bin/nextflow'), '-C', str(config), 'run',
                   str(ROOT / 'tests/nextflow/gplas_native.nf'), '-params-file', str(params),
                   '-work-dir', str(base / 'work'), '-with-trace', str(trace), '-ansi-log', 'false']
            cmd += ['-name', name] if phase == 'cold' else ['-resume', session]
            with (base / (phase + '.stdout')).open('w') as out, (base / (phase + '.stderr')).open('w') as err:
                result = subprocess.run(cmd, env=env, stdout=out, stderr=err, timeout=900)
            tasks = list(csv.DictReader(trace.open(), delimiter='\t')) if trace.exists() else []
            row = {'phase': phase, 'command': cmd, 'exit_code': result.returncode, 'tasks': tasks}
            runs.append(row)
            (base / 'progress.json').write_text(json.dumps(runs, indent=2) + '\n')
            if phase == 'bad-source':
                assert result.returncode != 0 and any(t['status'] == 'FAILED' for t in tasks)
                assert not any(t['status'] == 'CACHED' for t in tasks)
                assert 'GPLAS_PRODUCT=' not in (base / (phase + '.stdout')).read_text()
                assert not (base / 'bad-out/05_plasmid_binning/gplas2').exists()
                for task in tasks:
                    if task['status'] != 'FAILED': continue
                    path = next(Path(task['workdir']).glob('*.gplas_runtime.json'))
                    audit = json.loads(path.read_text())
                    assert audit['children'] == [] and 'Unsupported gplas source' in audit['error']
                continue
            assert result.returncode == 0 and len(tasks) == 2
            assert all(t['status'] == ('COMPLETED' if phase == 'cold' else 'CACHED') for t in tasks)
            if phase == 'cold':
                matching = [line.split('\t') for line in (ROOT / '.nextflow/history').read_text().splitlines()
                            if len(line.split('\t')) >= 6 and line.split('\t')[2] == name]
                assert len(matching) == 1
                session = str(uuid.UUID(matching[0][5]))
                row['session_uuid'] = session
            for record in records:
                products = base / 'out/05_plasmid_binning/gplas2' / (record['id'] + '.gplas2')
                check = base / (phase + '-' + record['id'] + '-independent.json')
                subprocess.run([str(args.prefix.resolve() / 'bin/python'), str(ROOT / 'tests/check_gplas_native.py'),
                                '--graph', record['graph'], '--products', str(products), '--name', record['id'],
                                '--output', str(check)], check=True)
                assert json.loads(check.read_text())['pass']
    finally:
        original.write_bytes(data); os.utime(original, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    result = {'pass': True, 'cold_session_uuid': session, 'source_sha256': source_hash,
              'source_unchanged': source_hash == {p: sha(ROOT / p) for p in files}, 'runs': runs,
              'mutation': {'before_sha256': hashlib.sha256(data).hexdigest(), 'bad_sha256': hashlib.sha256(bad).hexdigest(),
                           'bytes': len(data), 'mtime_ns': stamp.st_mtime_ns, 'private_copy_only': True},
              'scope': 'native fixed gplas IO on supplied classifications; altered second-sample DNA is an explicit transport counterfactual; exact UUID cache/source guard controls, not independent biological accuracy'}
    (base / 'run.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if result['source_unchanged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
