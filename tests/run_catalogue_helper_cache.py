#!/usr/bin/env python3
"""Real Nextflow helper-byte cache control; mutates only a private helper copy."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--nextflow', type=Path, required=True)
    p.add_argument('--work-dir', type=Path, required=True)
    p.add_argument('--contigs', type=Path, nargs='+', required=True)
    args = p.parse_args()
    base = args.work_dir.resolve()
    base.mkdir(parents=True, exist_ok=False)
    helper = base / 'builder.R'
    original = (ROOT / 'bin/plasmid_catalog_prepare.R').read_bytes()
    helper.write_bytes(original)
    stat = helper.stat()
    changed = original.replace(b'# Prepare a sample-aware', b'# prepare a sample-aware', 1)
    assert len(changed) == len(original) and changed != original
    config = base / 'native.config'
    config.write_text("process.executor='local'\nprocess.cpus=1\nprocess.memory='2 GB'\n"
                      "conda.enabled=false\ndocker.enabled=false\npodman.enabled=false\n"
                      "singularity.enabled=false\nparams.publish_dir_mode='copy'\n"
                      "trace.fields='task_id,hash,name,status,exit,workdir'\n")
    params = base / 'params.json'
    params.write_text(json.dumps({'contigs': [str(f.resolve()) for f in args.contigs],
                                 'catalogue_builder': str(helper), 'outdir': str(base / 'out')}))
    uuid = None
    runs = []
    products = None
    for phase, payload, expected in [('cold', original, 'COMPLETED'),
                                     ('unchanged', original, 'CACHED'),
                                     ('same-size-mtime-change', changed, 'COMPLETED'),
                                     ('restored', original, 'CACHED')]:
        helper.write_bytes(payload)
        os.utime(helper, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        log = base / (phase + '.nextflow.log')
        trace = base / (phase + '.trace.tsv')
        command = [str(args.nextflow.resolve()), '-log', str(log), '-C', str(config),
                   'run', str(ROOT / 'tests/nextflow/catalog_prepare_cache.nf'),
                   '-params-file', str(params), '-work-dir', str(base / 'work'),
                   '-with-trace', str(trace), '-ansi-log', 'false']
        if uuid:
            command += ['-resume', uuid]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        (base / (phase + '.console.log')).write_text(result.stdout + result.stderr)
        assert result.returncode == 0, (phase, result.stdout, result.stderr)
        if uuid is None:
            uuid = re.search(r'Session UUID: ([a-f0-9-]+)', log.read_text()).group(1)
        tasks = list(csv.DictReader(trace.open(), delimiter='\t'))
        assert len(tasks) == 1 and tasks[0]['status'] == expected and tasks[0]['exit'] == '0', tasks
        task = Path(tasks[0]['workdir'])
        assert (task / 'plasmid_catalog_prepare.R').read_bytes() == payload
        observed = {name: hashlib.sha256((task / name).read_bytes()).hexdigest()
                    for name in ['plasmid_catalog_input.fasta', 'catalogue_samples.tsv']}
        if products is None:
            products = observed
        assert products == observed
        runs.append({'phase': phase, 'command': command, 'task': tasks[0],
                     'helper_sha256': hashlib.sha256(payload).hexdigest(),
                     'helper_size': len(payload), 'helper_mtime_ns': helper.stat().st_mtime_ns})
        (base / 'run.json').write_text(json.dumps({'runs': runs, 'products_sha256': products,
            'pass': len(runs) == 4, 'scope': 'Helper content cache identity; no biological benchmark'}, indent=2) + '\n')
    assert (ROOT / 'bin/plasmid_catalog_prepare.R').read_bytes() == original
    print('PASS: cold / cached / same-size-mtime changed / restored cached')


if __name__ == '__main__':
    main()
