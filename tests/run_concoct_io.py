#!/usr/bin/env python3
"""Native fixed CONCOCT helpers in actual wrappers; independent DNA/BED checks.

The official composition fixture is fixed by Git blob. Controlled membership
is a file-format oracle, not a claimed biological clustering truth.
"""
import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from module_harness import render_module_harness
import random
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
COMPOSITION_BLOB = '47a32497a05a4a64bdcb0d6ceaa2f2c40b71e7ee'


def fasta(path):
    sequences = {}
    with (gzip.open(path, 'rt') if path.suffix.lower() == '.gz' else path.open()) as stream:
        for line in stream:
            if line.startswith('>'):
                cid = line[1:].split()[0]
                assert cid not in sequences
                sequences[cid] = ''
            else:
                sequences[cid] += line.strip()
    return sequences


def run(base, fixture, prefix, old_dir, cases):
    data = fixture.read_bytes()
    assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == COMPOSITION_BLOB
    original = fasta(fixture)
    f = base / 'fixtures'
    f.mkdir()
    plain = f / 'assembly sample.fna'
    shutil.copyfile(fixture, plain)
    for name in ['assembly sample.fna.gz', 'assembly sample.fna.GZ']:
        with gzip.open(f / name, 'wb') as stream:
            stream.write(data)
    compressed = f / 'assembly sample.fna.gz'
    upper = f / 'assembly sample.fna.GZ'
    broken = f / 'corrupt.fna.gz'
    broken.write_bytes(b'\x1f\x8bEXPLICITLY_CORRUPT_GZIP')
    membership = f / 'membership.csv'
    ids = list(original)
    # Deliberately two bins and omitted contigs. The oracle is specified before
    # calling the extractor, and verifies IDs/DNA instead of snapshot names.
    assigned = {cid: str(index % 2) for index, cid in enumerate(ids[:7])}
    membership.write_text('contig_id,cluster_id\n' + ''.join(cid + ',' + bid + '\n' for cid, bid in assigned.items()))
    empty = f / 'empty.csv'
    empty.write_text('contig_id,cluster_id\n')
    bad = f / 'unknown.csv'
    bad.write_text('contig_id,cluster_id\n__unknown_contig__,0\n')
    wrong = f / 'bad-header.csv'
    wrong.write_text('wrong,header\n' + ids[0] + ',0\n')
    rng = random.Random(1320)
    controlled = f / 'controlled.fna'
    controlled.write_text('>known\n' + ''.join(rng.choices('ACGT', k=2400)) + '\n')
    all_files = list(f.iterdir())
    initial_hashes = {q.name: hashlib.sha256(q.read_bytes()).hexdigest() for q in all_files}
    workflow = ROOT / 'tests/nextflow/concoct_io.nf'
    foreign_bin = base / 'foreign-source-bin'
    foreign_bin.mkdir()
    foreign = foreign_bin / 'cut_up_fasta.py'
    foreign.write_text("#!/usr/bin/env python\nraise SystemExit('UNREVIEWED_SOURCE_EXECUTED')\n")
    foreign.chmod(0o755)
    if old_dir:
        workflow = base / 'old-probe.nf'
        text = render_module_harness(ROOT / 'tests/nextflow/concoct_io.nf', '../../modules/nf-core/concoct/cutupfasta/main', old_dir / 'cutupfasta/main', 'run_concoct_cut_checked.py')
        for part in ['extractfastabins']:
            text = text.replace("'../../modules/nf-core/concoct/" + part + "/main'", repr(str(old_dir / part / 'main')))
        workflow.write_text(text)
    definitions = [
        ('cut-real-plain', 'cut', plain, None, '', True, None),
        ('cut-real-gzip', 'cut', compressed, None, '', True, None),
        ('cut-real-upper', 'cut', upper, None, '', True, None),
        ('cut-default-overlap', 'cut', controlled, None, '', True, None),
        ('cut-nonoverlap-merge', 'cut', controlled, None, '-c 500 -o 0 --merge_last', True, None),
        ('cut-no-bed', 'cut', controlled, None, '', False, None),
        ('cut-corrupt-gzip', 'cut', broken, None, '', True, 'gzip'),
        ('cut-invalid-step', 'cut', controlled, None, '-c 100 -o 100', True, 'AssertionError'),
        ('cut-source-mismatch', 'cut', controlled, None, '', True, 'source differs from reviewed1.1.0'),
        ('extract-real-plain', 'extract', plain, membership, '', False, None),
        ('extract-real-gzip', 'extract', compressed, membership, '', False, None),
        ('extract-real-upper', 'extract', upper, membership, '', False, None),
        ('extract-empty-plain', 'extract', plain, empty, '', False, None),
        ('extract-empty-gzip', 'extract', compressed, empty, '', False, None),
        ('extract-unknown', 'extract', compressed, bad, '', False, 'KeyError'),
        ('extract-bad-header', 'extract', plain, wrong, '', False, "Header line was not"),
        ('extract-corrupt-gzip', 'extract', broken, membership, '', False, 'gzip')
    ]
    runs = []
    for name, mode, assembly, table, args, bed, error in definitions:
        if cases and name not in cases:
            continue
        p = base / name
        p.mkdir()
        config = p / 'config'
        config.write_text("includeConfig '" + str(ROOT / 'conf/nfcore_mag.config') + "'\n"
                          "params.publish_dir_mode='copy'\nprocess.executor='local'\nprocess.cpus=1\n"
                          "process.memory='512 MB'\nprocess.maxForks=1\nconda.enabled=false\n"
                          "docker.enabled=false\nsingularity.enabled=false\n"
                          "process { withName: 'CONCOCT_CUTUPFASTA' { ext.args='" + args + "' } }\n")
        params = {'mode': mode, 'bed': bed, 'records': [{'id': 'sample', 'fasta': str(assembly), 'csv': str(table) if table else None}], 'outdir': str(p / 'out')}
        (p / 'params.json').write_text(json.dumps(params))
        command = [str(ROOT / 'results/tool-audit/runtime/bin/nextflow'), '-C', str(config), 'run', str(workflow), '-params-file', str(p / 'params.json'), '-work-dir', str(p / 'work'), '-with-trace', str(p / 'trace.tsv'), '-ansi-log', 'false']
        env = os.environ.copy()
        env['PATH'] = str(prefix / 'bin') + ':' + env['PATH']
        if name == 'cut-source-mismatch':
            env['PATH'] = str(foreign_bin) + ':' + env['PATH']
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        (p / 'stdout.log').write_text(result.stdout)
        (p / 'stderr.log').write_text(result.stderr)
        tasks = list(csv.DictReader((p / 'trace.tsv').open(), delimiter='\t')) if (p / 'trace.tsv').exists() else []
        checks = {}
        out = p / 'out/07_host_prediction/mag/concoct'
        if error:
            task_errors = '\n'.join(q.read_text() for q in (p / 'work').rglob('.command.err'))
            checks = {'failed': result.returncode != 0, 'diagnostic_from_task_stderr': ('gzip:' if error == 'gzip' else error) in task_errors, 'one_failed_task': len(tasks) == 1 and tasks[0]['status'] == 'FAILED', 'no_partial_published_files': not [q for q in out.rglob('*') if q.is_file()]}
        else:
            checks = {'success': result.returncode == 0, 'one_completed_task': len(tasks) == 1 and tasks[0]['status'] == 'COMPLETED'}
            if checks['success'] and mode == 'cut':
                parts = fasta(out / 'cutup_fasta/sample.fasta')
                source = fasta(assembly)
                bed_path = out / 'cutup_fasta/sample.bed'
                checks['bed_presence'] = bed_path.exists() == bed
                # Actual upstream legacy helper is the unchanged-DNA control.
                baseline = subprocess.run([str(prefix / 'bin/cut_up_fasta.py'), str(plain if assembly in [plain, compressed, upper] else assembly)] + args.split(), env=env, capture_output=True, text=True)
                assert baseline.returncode == 0
                checks['sliced_DNA_unchanged'] = (out / 'cutup_fasta/sample.fasta').read_text() == baseline.stdout
                if bed:
                    rows = list(csv.reader(bed_path.open(), delimiter='\t'))
                    checks['one_interval_per_part'] = len(rows) == len(parts) and {r[3] for r in rows} == set(parts)
                    checks['BED_bounds_and_exact_DNA'] = all(r[0] in source and 0 <= int(r[1]) < int(r[2]) <= len(source[r[0]]) and source[r[0]][int(r[1]):int(r[2])] == parts[r[3]] for r in rows)
                    if name == 'cut-default-overlap':
                        checks['known_stride_99_and_last_boundary'] = len(rows) == 25 and rows[1][1:3] == ['99', '2098'] and rows[-1][1:3] == ['2376', '2400']
                    elif name == 'cut-nonoverlap-merge':
                        checks['independent_500bp_nonoverlap_merge'] = [(int(r[1]), int(r[2])) for r in rows] == [(0, 500), (500, 1000), (1000, 1500), (1500, 2400)]
            elif checks['success']:
                bins = list((out / 'bins').rglob('*.fa.gz'))
                expected = {} if 'empty' in name else {'sample_' + bid + '.fa.gz': {cid: original[cid] for cid, cluster in assigned.items() if cluster == bid} for bid in ['0', '1']}
                checks['exact_expected_bins_IDs_DNA'] = {q.name: fasta(q) for q in bins} == expected
                checks['no_fake_empty_FASTA'] = bool('EXTRACTED_BINS=' in result.stdout) == bool(expected)
        checks['all_inputs_unchanged'] = initial_hashes == {q.name: hashlib.sha256(q.read_bytes()).hexdigest() for q in all_files}
        runs.append({'case': name, 'command': command, 'exit': result.returncode, 'checks': checks, 'tasks': tasks})
        print(name, checks, flush=True)
        sources = ['bin/run_concoct_cut_checked.py', 'modules/nf-core/concoct/cutupfasta/main.nf', 'modules/nf-core/concoct/extractfastabins/main.nf', 'tests/nextflow/concoct_io.nf', 'tests/run_concoct_io.py']
        receipt = {'runs': runs, 'pass': all(all(r['checks'].values()) for r in runs), 'source_sha256': {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in sources}, 'module_override': str(old_dir) if old_dir else None, 'limitations': ['actual native CONCOCT1.1.0 helpers in original/fixed wrappers; exact upstream source checked', 'official real DNA plus explicitly controlled membership/negative inputs; not clustering accuracy or native full MAG/image/nf-test framework certification', 'BED checked directly against original DNA; actual legacy helper checks unchanged sliced DNA; no altered scoring/cut defaults']}
        (base / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt['pass']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', required=True, type=Path)
    parser.add_argument('--fixture', required=True, type=Path)
    parser.add_argument('--prefix', required=True, type=Path)
    parser.add_argument('--old-dir', type=Path)
    parser.add_argument('--cases', default='')
    args = parser.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    raise SystemExit(0 if run(args.work_dir.resolve(), args.fixture.resolve(), args.prefix.resolve(), args.old_dir.resolve() if args.old_dir else None, args.cases.split(',') if args.cases else []) else 1)
