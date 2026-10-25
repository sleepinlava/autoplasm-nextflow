#!/usr/bin/env python3
"""Actual main-entry rejection controls for complete per-sample PlasX resources."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ['plasx_anvio_source', 'plasx_source', 'plasx_cog_db', 'plasx_pfam_db', 'plasx_profiles', 'plasx_model']


def run(base, replay):
    base.mkdir(parents=True, exist_ok=False)
    fixture = base / 'fixture'
    fixture.mkdir()
    (fixture / 'samples.tsv').write_text('sample_id\tassembly\nS1\tunused.fa\n')
    (fixture / 'model.tsv').write_text('RESOURCE_VALIDATION_ONLY\n')
    for folder, names in [('anvio', ['anvio/__init__.py', 'bin/anvi-gen-contigs-database', 'bin/anvi-export-gene-calls',
                                    'bin/anvi-run-ncbi-cogs', 'bin/anvi-run-pfams', 'bin/anvi-export-functions']),
                          ('plasx', ['plasx/model.py', 'plasx/mmseqs.py', 'plasx/plasx_script.py'])]:
        for name in names:
            path = fixture / folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('RESOURCE_VALIDATION_ONLY\n')
    options = {name: [] for name in ['polishing_tools', 'plasmid_binning_tools', 'typing_tools', 'typing_optional_tools',
               'host_prediction_tools', 'mag_tools', 'host_linking_methods', 'host_linking_optional_methods', 'annotation_tools',
               'annotation_optional_tools', 'comparative_tools', 'comparative_optional_tools']}
    options.update(platform='assembly', samplesheet=str(fixture / 'samples.tsv'), genomad_db=str(fixture),
                   host_plasmid_linking=False, plasmid_detection_tools=['genomad', 'plasx'], plasx_splits=32,
                   plasx_anvio_source=str(fixture / 'anvio'), plasx_source=str(fixture / 'plasx'),
                   plasx_cog_db=str(fixture), plasx_pfam_db=str(fixture), plasx_profiles=str(fixture),
                   plasx_model=str(fixture / 'model.tsv'))
    cases = []
    if replay:
        for row in csv.DictReader((ROOT / 'docs/tool-audit/p0-main-cases.tsv').open(), delimiter='\t'):
            if row['case'].startswith('plasx-'):
                continue
            cases.append((row['case'], json.loads((ROOT / row['artifacts'] / 'params.json').read_text()), row['stderr_diagnostic'], False))
    for resource in RESOURCES:
        cases.append(('plasx-missing-' + resource, dict(options, **{resource: None}), 'an enabled tool requires --' + resource, True))
    cases += [('plasx-retired-shared-annotations', dict(options, plasx_annotations=str(fixture / 'model.tsv')), '--plasx_annotations is retired', True),
              ('plasx-source-not-directory', dict(options, plasx_source=str(fixture / 'model.tsv')), '--plasx_source must be a directory', True),
              ('plasx-model-not-file', dict(options, plasx_model=str(fixture)), '--plasx_model must be a coefficient table file', True),
              ('plasx-anvio-missing-program', dict(options, plasx_anvio_source=str(fixture)), '--plasx_anvio_source missing source file anvio/__init__.py', True),
              ('plasx-missing-program', dict(options, plasx_source=str(fixture)), '--plasx_source missing source file plasx/model.py', True)]
    for value in [-1, 1.5, 'invalid']:
        cases.append(('plasx-invalid-splits-' + str(value), dict(options, plasx_splits=value), '--plasx_splits must be a nonnegative integer', True))
    source_sha = hashlib.sha256((ROOT / 'main.nf').read_bytes()).hexdigest()

    def execute(case):
        name, parameters, diagnostic, new = case
        directory = base / name
        directory.mkdir()
        parameters['outdir'] = str(directory / 'out')
        (directory / 'params.json').write_text(json.dumps(parameters, indent=2) + '\n')
        command = [str(ROOT / 'results/tool-audit/runtime/bin/nextflow'), '-C',
                   str(ROOT / 'results/tool-audit/20261020-main-p0/combined.config'), 'run', str(ROOT / 'main.nf'),
                   '-params-file', str(directory / 'params.json'), '-work-dir', str(directory / 'work'),
                   '-with-trace', str(directory / 'trace.tsv'), '-ansi-log', 'false']
        process = subprocess.run(command, capture_output=True, text=True)
        (directory / 'stdout.log').write_text(process.stdout)
        (directory / 'stderr.log').write_text(process.stderr)
        tasks = list(csv.DictReader((directory / 'trace.tsv').open(), delimiter='\t')) if (directory / 'trace.tsv').exists() else []
        checks = {'rejected': process.returncode != 0, 'precise_diagnostic': diagnostic in process.stdout + process.stderr,
                  'zero_tasks': not tasks, 'zero_commands': not list((directory / 'work').rglob('.command.sh'))}
        row = {'case': name, 'new_case': new, 'artifacts': str(directory.relative_to(ROOT)), 'command': command,
               'exit': process.returncode, 'stderr_diagnostic': diagnostic, 'checks': checks}
        print(name, checks, flush=True)
        return row

    with ThreadPoolExecutor(max_workers=2) as executor:
        rows = list(executor.map(execute, cases))
    assert hashlib.sha256((ROOT / 'main.nf').read_bytes()).hexdigest() == source_sha
    receipt = {'pass': all(all(row['checks'].values()) for row in rows), 'main_sha256': source_sha, 'runs': rows,
               'new_cases': sum(row['new_case'] for row in rows),
               'scope': 'actual main rejection paths, all zero analysis tasks; replays do not increase unique-case denominator; no successful end-to-end or scientific validation'}
    (base / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt['pass']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--replay-old', action='store_true')
    args = parser.parse_args()
    raise SystemExit(0 if run(args.output.resolve(), args.replay_old) else 1)
