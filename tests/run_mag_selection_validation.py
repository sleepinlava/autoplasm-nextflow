#!/usr/bin/env python3
"""Replay registered main rejections and the explicit MAG dependency matrix.

Runs actual main and MAG_HOST; no copied implementation/validator logic.
Replays do not add independent cases to the audit registry.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

NEW_CASES = [
    ('mag-metabat-concoct-no-das', ['metabat2', 'concoct'], 'Multiple MAG binners require explicitly selecting das_tool'),
    ('mag-metabat-semibin-no-das', ['metabat2', 'semibin'], 'Multiple MAG binners require explicitly selecting das_tool'),
    ('mag-concoct-semibin-no-das', ['concoct', 'semibin'], 'Multiple MAG binners require explicitly selecting das_tool'),
    ('mag-all-no-das', ['metabat2', 'concoct', 'semibin'], 'Multiple MAG binners require explicitly selecting das_tool'),
    ('mag-das-no-binner', ['das_tool'], '--mag_tools requires at least one binner'),
    ('mag-checkm-no-binner', ['checkm2'], '--mag_tools requires at least one binner'),
    ('mag-gtdb-no-binner', ['gtdbtk'], '--mag_tools requires at least one binner'),
    ('mag-quality-no-binner', ['checkm2', 'gtdbtk', 'das_tool'], '--mag_tools requires at least one binner')
]


def run(base, replay):
    cases = []
    if replay:
        for row in csv.DictReader((ROOT / 'docs/tool-audit/p0-main-cases.tsv').open(), delimiter='\t'):
            if row['case'] not in {r[0] for r in NEW_CASES}:
                params = json.loads((ROOT / row['artifacts'] / 'params.json').read_text())
                cases.append((row['case'], params, row['stderr_diagnostic']))
    cases += [(case, {'mag_tools': selection}, diagnostic) for case, selection, diagnostic in NEW_CASES]
    runs = []
    for scope, values in [('main', cases), ('direct-MAG_HOST', [(case, {'mag_tools': selection, 'records': []}, diagnostic) for case, selection, diagnostic in NEW_CASES])]:
        for name, params, diagnostic in values:
            p = base / scope / name
            p.mkdir(parents=True)
            params['outdir'] = str(p / 'out')
            (p / 'params.json').write_text(json.dumps(params))
            script = ROOT / ('main.nf' if scope == 'main' else 'tests/nextflow/mag_selection.nf')
            command = [str(ROOT / 'results/tool-audit/runtime/bin/nextflow'), '-C', str(ROOT / 'results/tool-audit/20261020-main-p0/combined.config'), 'run', str(script), '-params-file', str(p / 'params.json'), '-work-dir', str(p / 'work'), '-with-trace', str(p / 'trace.tsv'), '-ansi-log', 'false']
            result = subprocess.run(command, capture_output=True, text=True)
            (p / 'stdout.log').write_text(result.stdout)
            (p / 'stderr.log').write_text(result.stderr)
            tasks = list(csv.DictReader((p / 'trace.tsv').open(), delimiter='\t')) if (p / 'trace.tsv').exists() else []
            commands = list((p / 'work').rglob('.command.sh'))
            checks = {'rejected': result.returncode != 0, 'precise_diagnostic': diagnostic in result.stdout + result.stderr, 'zero_tasks': not tasks, 'zero_command_files': not commands}
            runs.append({'scope': scope, 'case': name, 'stderr_diagnostic': diagnostic, 'command': command, 'exit': result.returncode, 'artifacts': str(p.relative_to(ROOT)), 'checks': checks})
            print(scope, name, checks, flush=True)
            receipt = {'runs': runs, 'expected_runs': len(cases) + len(NEW_CASES), 'pass': len(runs) == len(cases) + len(NEW_CASES) and all(all(r['checks'].values()) for r in runs), 'main_sha256': hashlib.sha256((ROOT / 'main.nf').read_bytes()).hexdigest(), 'source_sha256': {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in ['main.nf', 'lib/mag_selection.nf', 'subworkflows/mag_host.nf', 'tests/run_mag_selection_validation.py']}, 'limitations': ['actual rejection paths with zero analysis tasks; not successful main end-to-end or nf-test framework certification', 'new unique main MAG scenarios=8; direct include checks and replays are not new main cases']}
            (base / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt['pass']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', required=True, type=Path)
    parser.add_argument('--replay-main-registry', action='store_true')
    args = parser.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    raise SystemExit(0 if run(args.work_dir.resolve(), args.replay_main_registry) else 1)
