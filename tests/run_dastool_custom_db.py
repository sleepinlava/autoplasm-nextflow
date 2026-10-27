#!/usr/bin/env python3
"""Actual native DAS1.1.7 optional DB, fixed full dataset and independent oracle.

Positive custom DBs are complete package data with verified package hashes.
The explicit nonmatching-lookup negative proves that the supplied DB is read,
including when its source basename is 'db' (reserved by the upstream CLI).
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from prepare_dastool_sample import verify
from run_dastool_export import ROOT, fasta

DB_FILES = ['bac.all.faa', 'bac.scg.faa', 'bac.scg.lookup', 'arc.all.faa', 'arc.scg.faa', 'arc.scg.lookup']


def db_hashes(path):
    if not path:
        return {}
    if path.is_file():
        return {path.name: hashlib.sha256(path.read_bytes()).hexdigest()}
    return {q.name: hashlib.sha256(q.read_bytes()).hexdigest() for q in path.iterdir() if q.is_file()}


def run(base, fixture, prefix, proteins, old_module, cases):
    verify(fixture)
    metadata = json.loads(next((prefix / 'conda-meta').glob('das_tool-*.json')).read_text())
    assert metadata['version'] == '1.1.7' and metadata['build'] == 'r44hdfd78af_1'
    lock = json.loads((ROOT / 'tests/dastool-db.lock.json').read_text())
    assert metadata['sha256'] == lock['package']['sha256']
    reference_db = prefix / 'share/das_tool-1.1.7-1/db'
    expected_paths = {Path(row['_path']).name: row for row in metadata['paths_data']['paths'] if '/db/' in row['_path']}
    original_db_hashes = db_hashes(reference_db)
    assert set(original_db_hashes) == set(DB_FILES)
    assert original_db_hashes == {row['name']: row['sha256'] for row in lock['files']}
    for name in DB_FILES:
        assert original_db_hashes[name] == expected_paths[name]['sha256']
    sources = base / 'database-inputs'
    sources.mkdir()
    space = sources / 'complete custom database'
    named_db = sources / 'named/db'
    negative = sources / 'controlled-negative/db'
    missing = sources / 'incomplete database'
    empty = sources / 'empty file database'
    for path in [space, named_db, negative, missing, empty]:
        shutil.copytree(reference_db, path)
    (missing / 'arc.scg.lookup').unlink()
    (empty / 'bac.scg.faa').write_bytes(b'')
    for name in ['bac.scg.lookup', 'arc.scg.lookup']:
        (negative / name).write_text('CONTROLLED_NO_MATCH_PROTEIN\tCONTROLLED_ONLY\n')
    not_dir = sources / 'not a directory'
    not_dir.write_text('EXPLICIT_INVALID_DB_INPUT\n')
    raw_input_hashes = {str(path.relative_to(sources)): db_hashes(path) for path in [space, named_db, negative, missing, empty, not_dir]}
    expected_proteins = hashlib.sha256(proteins.read_bytes()).hexdigest()
    assembly = fixture / 'sample.human.gut_contigs.fa'
    predictions = [fixture / ('sample.human.gut_' + name + '_contigs2bin.tsv') for name in ['concoct', 'maxbin2', 'metabat', 'tetraESOM']]
    original = fasta(assembly)
    expected_bins = {}
    for cid, bid in csv.reader((fixture / 'DASToolRun1_DASTool_contig2bin.tsv').open(), delimiter='\t'):
        expected_bins.setdefault(bid, {})[cid] = original[cid]
    assert len(expected_bins) == 15
    workflow = ROOT / 'tests/nextflow/dastool_custom_db.nf'
    if old_module:
        before = base / 'before-probe.nf'
        before.write_text(workflow.read_text().replace("'../../modules/nf-core/dastool/dastool/main'", repr(str(old_module.with_suffix(''))))
            .replace("'../../lib/resource_inputs'",repr(str(ROOT/'lib/resource_inputs')))
            .replace('Channel.value(resourceInput(params.db_dir ?: null))','params.db_dir ? file(params.db_dir,checkIfExists:true) : []'))
    definitions = [('custom-space', space, None, None), ('custom-named-db', named_db, proteins, None), ('default-db', None, None, None),
                   ('missing-file', missing, proteins, 'DAS Tool custom database is missing or empty: arc.scg.lookup'),
                   ('empty-file', empty, proteins, 'DAS Tool custom database is missing or empty: bac.scg.faa'),
                   ('not-directory', not_dir, proteins, 'DAS Tool custom database must be a directory'),
                   ('no-matching-lookup', negative, proteins, 'No single copy genes predicted')]
    if old_module:
        definitions.insert(0, ('before', space, None, 'ORIGINAL_CLI_REJECTION'))
    runs = []
    for name, database, protein_input, error in definitions:
        if cases and name not in cases:
            continue
        p = base / name
        p.mkdir()
        config = p / 'config'
        config.write_text("includeConfig '" + str(ROOT / 'conf/nfcore_mag.config') + "'\n"
                          "params.publish_dir_mode='copy'\nprocess.executor='local'\nprocess.cpus=1\n"
                          "process.memory='3 GB'\nprocess.maxForks=1\nconda.enabled=false\n"
                          "docker.enabled=false\nsingularity.enabled=false\n")
        params = {'assembly': str(assembly), 'predictions': list(map(str, predictions)), 'db_dir': str(database) if database else None, 'proteins': str(protein_input) if protein_input else None, 'outdir': str(p / 'out')}
        (p / 'params.json').write_text(json.dumps(params))
        command = [str(ROOT / 'results/tool-audit/runtime/bin/nextflow'), '-C', str(config), 'run', str(before if name == 'before' else workflow), '-params-file', str(p / 'params.json'), '-work-dir', str(p / 'work'), '-with-trace', str(p / 'trace.tsv'), '-ansi-log', 'false']
        env = os.environ.copy()
        env['PATH'] = str(prefix / 'bin') + ':' + env['PATH']
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        (p / 'stdout.log').write_text(result.stdout)
        (p / 'stderr.log').write_text(result.stderr)
        tasks = list(csv.DictReader((p / 'trace.tsv').open(), delimiter='\t')) if (p / 'trace.tsv').exists() else []
        scripts = list((p / 'work').rglob('.command.sh'))
        task_stderr = '\n'.join(q.read_text() for q in (p / 'work').rglob('.command.err'))
        task_stdout = '\n'.join(q.read_text() for q in (p / 'work').rglob('.command.out'))
        out = p / 'out/07_host_prediction/mag/das_tool'
        checks = {}
        if error:
            checks = {'failed': result.returncode != 0, 'one_failed_task': len(tasks) == 1 and tasks[0]['status'] == 'FAILED', 'no_partial_published_files': not [q for q in out.rglob('*') if q.is_file()]}
            if name == 'before':
                checks['original_misspelt_flag'] = len(scripts) == 1 and '--db_directory' in scripts[0].read_text()
                checks['no_query_products'] = not list((p / 'work').rglob('*.seqlength'))
                checks['actual_CLI_error'] = 'Argument' in task_stderr or 'Usage:' in task_stdout
            elif name == 'no-matching-lookup':
                logs = list((p / 'work').rglob('DASToolRun1_DASTool.log'))
                checks['actual_custom_DB_read_negative'] = len(logs) == 1 and error in logs[0].read_text()
            else:
                checks['precise_preflight_diagnostic'] = error in task_stderr
                checks['query_not_started'] = 'DAS Tool 1.1.7' not in task_stdout and not list((p / 'work').rglob('*.seqlength'))
        else:
            checks = {'success': result.returncode == 0, 'one_completed_task': len(tasks) == 1 and tasks[0]['status'] == 'COMPLETED'}
            if checks['success']:
                actual = {q.stem: fasta(q) for q in out.glob('*_DASTool_bins/*.fa')}
                checks['fifteen_independent_memberships_and_all_DNA'] = actual == expected_bins
                rows = list(csv.DictReader((out / 'DASToolRun1_DASTool_summary.tsv').open(), delimiter='\t'))
                checks['independent_bin_sizes_and_counts'] = len(rows) == 15 and all(int(row['size']) == sum(map(len, expected_bins[row['bin']].values())) and int(row['contigs']) == len(expected_bins[row['bin']]) for row in rows)
        if name != 'before':
            checks['correct_option_and_fixed_staging_name'] = len(scripts) == 1 and ('--dbDirectory dastool_db' in scripts[0].read_text()) == bool(database)
            if database:
                checks['actual_directory_or_file_staged_from_declared_source'] = len(scripts) == 1 and scripts[0].parent.joinpath('dastool_db').samefile(database)
        checks['all_custom_inputs_unchanged'] = raw_input_hashes == {str(path.relative_to(sources)): db_hashes(path) for path in [space, named_db, negative, missing, empty, not_dir]}
        checks['bundled_database_unchanged'] = db_hashes(reference_db) == original_db_hashes
        checks['real_predicted_proteins_unchanged'] = hashlib.sha256(proteins.read_bytes()).hexdigest() == expected_proteins
        runs.append({'case': name, 'command': command, 'exit': result.returncode, 'checks': checks, 'tasks': tasks})
        print(name, checks, flush=True)
        source_paths = ['modules/nf-core/dastool/dastool/main.nf', 'conf/nfcore_mag.config', 'tests/nextflow/dastool_custom_db.nf', 'tests/run_dastool_custom_db.py']
        receipt = {'runs': runs, 'pass': all(all(r['checks'].values()) for r in runs), 'source_sha256': {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in source_paths}, 'original_module': str(old_module) if old_module else None, 'native_package': {key: metadata[key] for key in ['url', 'sha256', 'version', 'build']}, 'full_positive_database_sha256': original_db_hashes, 'real_predicted_proteins_sha256': expected_proteins, 'limitations': ['actual native DAS1.1.7, complete packaged positive DB, full official gut sample and fixed independent15-bin expected products', 'nonmatching lookup DB is a deliberate negative control with full real reference FASTAs but fabricated unmatched lookup IDs; not a biological DB/sensitivity benchmark', 'positive/default runs keep production score0.5/export flag; no native model/image/nf-test/full platform certification for other tools']}
        (base / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt['pass']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', required=True, type=Path)
    parser.add_argument('--fixture-dir', required=True, type=Path)
    parser.add_argument('--prefix', required=True, type=Path)
    parser.add_argument('--proteins', required=True, type=Path, help='Actual Prodigal proteins from the same official assembly/native DAS control')
    parser.add_argument('--old-module', type=Path)
    parser.add_argument('--cases', default='')
    args = parser.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    raise SystemExit(0 if run(args.work_dir.resolve(), args.fixture_dir.resolve(), args.prefix.resolve(), args.proteins.resolve(), args.old_module.resolve() if args.old_module else None, args.cases.split(',') if args.cases else []) else 1)
