#!/usr/bin/env python3
"""Native fixed1.42 DESEQ2 and original CROSS_SAMPLE on explicit count fixtures.

A separate wide-matrix official API oracle checks full-model contrasts; this is
an execution/numerical contract check, not biological differential accuracy.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    with path.open() as stream:
        return list(csv.DictReader(stream, delimiter='\t'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(folder, kind):
    folder.mkdir()
    n = 4 if kind == 'two' else 9 if kind == 'three' else 7 if kind == 'ungrouped' else 6
    ids = ['001', '1', 'NA'] + [f'S{i}' for i in range(3, n)]
    groups = ['A'] * (n // 2) + ['B'] * (n - n // 2)
    if kind == 'three': groups = ['A'] * 3 + ['B'] * 3 + ['C'] * 3
    if kind == 'ungrouped': groups = ['A'] * 3 + ['B'] * 3 + ['']
    features = [] if kind == 'empty' else ['001', '1', 'NA'] + [f'F{i}' for i in range(3, 100)]
    rng = random.Random(321)
    values = []
    for j in range(len(features)):
        row = []
        for i in range(n):
            mean = (60 if groups[i] == 'A' else 1200) if 3 <= j < 8 else 50 + j * 3
            count = max(1, round(rng.gauss(mean, .2 * mean)))
            if kind == 'all-zero' or (kind == 'zero-sample' and i == 0): count = 0
            if kind == 'low': count = 1 + (i + j) % 9
            if kind == 'invalid-count' and i == 0 and j == 0: count = ''
            row.append(count)
        values.append(row)
    if kind == 'quoted': groups = ['"A\tcontrol'] * 3 + ['"B\ncase'] * 3
    with (folder / 'samples.tsv').open('w') as stream:
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        writer.writerow(['sample_id', 'group'])
        writer.writerows(zip(ids, groups))
    for role, column in [('plasmids', 'plasmid_id'), ('contigs', 'contig_id')]:
        with (folder / (role + '.tsv')).open('w') as stream:
            writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
            writer.writerow([column, 'sample_id', 'raw_count', 'coverage'])
            for fid, row in zip(features, values):
                for sid, count in zip(ids, row): writer.writerow([fid, sid, count, '0.125'])
    with (folder / 'wide.tsv').open('w') as stream:
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        writer.writerow(['plasmid_id', *ids])
        writer.writerows([fid, *row] for fid, row in zip(features, values))
    with (folder / 'states.tsv').open('w') as stream:
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        writer.writerow(['sample_id', 'reference_features', 'plasmid_features', 'eligible_read_alignments', 'plasmid_read_alignments', 'quantification_status'])
        for i, sid in enumerate(ids):
            total = sum(row[i] for row in values if isinstance(row[i], int))
            state = 'empty_catalogue' if not features else 'measured_zero' if not total else 'measured'
            writer.writerow([sid, len(features), len(features), total, total, state])
            d = folder / sid
            d.mkdir()
            dna = random.Random(222)
            sequences = [''.join(dna.choices('ACGT', k=1200)) for _ in features]
            (d / 'plasmids.fasta').write_text(''.join(f'>{fid}\n{seq}\n' for fid, seq in zip(features, sequences)))
            (d / 'consensus.tsv').write_text('sample_id\tcontig_id\tplasmid_call\tsupporting_tools\n' + ''.join(f'{sid}\t{fid}\tplasmid\tcontrolled_fixture\n' for fid in features))
            (d / 'structure.tsv').write_text('sample_id\tplasmid_id\tis_circular\n' + ''.join(f'{sid}\t{fid}\tfalse\n' for fid in features))
    return ids, features


def compare(actual, expected):
    def keyed(rows): return {(r['plasmid_id'], r['group_a'], r['group_b']): r for r in rows}
    a, e = keyed(actual), keyed(expected)
    assert len(a) == len(actual) and set(a) == set(e)
    for key in a:
        for field in ['log2_fold_change', 'p_value', 'q_value']:
            av, ev = a[key][field], e[key][field]
            assert (av == '') == (ev == ''), (key, field, av, ev)
            if av:
                assert math.isfinite(float(av))
                assert math.isclose(float(av), float(ev), rel_tol=1e-8, abs_tol=1e-12), (key, field, av, ev)
        assert a[key]['method'] == 'DESeq2' and a[key]['warnings'] == ''
    labels = sorted({r[field] for r in actual for field in ['group_a', 'group_b']})
    planted = [r for r in actual if r['plasmid_id'] in {f'F{i}' for i in range(3, 8)} and r['group_a'] == labels[0] and r['group_b'] == labels[1]]
    assert len(planted) == 5 and all(float(r['log2_fold_change']) < -3 and float(r['q_value']) < .01 for r in planted)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--deseq-prefix', type=Path, required=True)
    parser.add_argument('--python-prefix', type=Path, required=True)
    parser.add_argument('--before-dir', type=Path, required=True)
    a = parser.parse_args()
    base = a.work_dir.resolve()
    base.mkdir(parents=True, exist_ok=False)
    prefix, python, before = a.deseq_prefix.resolve(), a.python_prefix.resolve(), a.before_dir.resolve()
    sources = ['bin/deseq2_plasmid.R', 'bin/statistics_input_contract.R', 'modules/cross_sample/deseq2.nf',
               'subworkflows/cross_sample.nf', 'modules/cross_sample/statistics_inputs.nf',
               'bin/differential_abundance.R', 'modules/cross_sample/differential.nf',
               'modules/cross_sample/report.nf', 'bin/generate_report.R', 'lib/report_events.nf',
               'tests/nextflow/deseq2_model.nf', 'tests/nextflow/statistics_eligibility.nf',
               'tests/deseq2_reference.R', 'tests/run_deseq2_model.py']
    hashes = {n: sha(ROOT / n) for n in sources}
    env = os.environ.copy()
    env['PATH'] = str(python / 'bin') + ':' + str(ROOT / 'bin') + ':' + env['PATH']
    model_env = env.copy()
    model_env['PATH'] = str(prefix / 'bin') + ':' + env['PATH']
    model_env['R_LIBS_USER'] = model_env['R_LIBS_SITE'] = str(prefix / 'lib/R/library')
    check = subprocess.run([str(prefix / 'bin/Rscript'), '-e', 'cat(as.character(packageVersion("DESeq2")))'], env=model_env, text=True, capture_output=True, check=True)
    assert check.stdout.strip() == '1.42.0'
    setup = 'export PATH=' + shlex.quote(str(prefix / 'bin')) + ':"$PATH"\nexport R_LIBS_USER=' + shlex.quote(str(prefix / 'lib/R/library')) + '\nexport R_LIBS_SITE=' + shlex.quote(str(prefix / 'lib/R/library'))
    literal_setup = "'" + setup.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n") + "'"
    config = base / 'native.config'
    config.write_text("process.executor='local'\nprocess.cpus=1\nprocess.memory='1 GB'\nprocess.maxForks=1\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\ntrace.fields='task_id,hash,name,status,exit,workdir'\nprocess { withName: 'DESEQ2' { beforeScript = " + literal_setup + ' } }\n')
    runs, oracles, case_state = [], {}, {}
    cases = [('before-positive', 'positive', 3, True), ('before-zero', 'all-zero', 3, True), ('before-two', 'two', 2, True),
             ('positive', 'positive', 3, False), ('three', 'three', 3, False), ('quoted', 'quoted', 3, False), ('two-min2', 'two', 2, False),
             ('two-default3', 'two', 3, False), ('raised-min4', 'positive', 4, False), ('all-zero', 'all-zero', 3, False),
             ('zero-sample', 'zero-sample', 3, False), ('empty', 'empty', 3, False), ('low', 'low', 3, False),
             ('ungrouped', 'ungrouped', 3, False), ('invalid-min0', 'positive', 0, False), ('invalid-count', 'invalid-count', 3, False),
             ('positive-resume', 'positive', 3, False), ('positive-resume-raised', 'positive', 4, False),
             ('cross-positive', 'positive', 3, False), ('cross-unchanged', 'positive', 3, False), ('cross-raised', 'positive', 4, False),
             ('cross-zero', 'all-zero', 3, False), ('cross-invalid', 'positive', 0, False)]
    expected_reasons = {'two-default3': 'insufficient_replication', 'raised-min4': 'insufficient_replication',
                        'positive-resume-raised': 'insufficient_replication', 'cross-raised': 'insufficient_replication',
                        'all-zero': 'all_zero_counts', 'cross-zero': 'all_zero_counts', 'zero-sample': 'zero_count_samples',
                        'empty': 'zero_features', 'low': 'no_features_after_count_filter'}
    for name, kind, minimum, old in cases:
        resume = name in ['positive-resume', 'positive-resume-raised', 'cross-unchanged', 'cross-raised']
        cross = name.startswith('cross-')
        reuse = 'cross-positive' if cross else 'positive'
        if resume:
            d, fixture, ids, features, harness, params = case_state[reuse]
            params = dict(params, min_group_replicates=minimum)
        else:
            d = base / name
            d.mkdir()
            fixture = d / 'fixtures'
            ids, features = generate(fixture, kind)
            harness = ROOT / ('tests/nextflow/statistics_eligibility.nf' if cross else 'tests/nextflow/deseq2_model.nf')
            if old:
                harness = d / 'old-node.nf'
                harness.write_text((ROOT / 'tests/nextflow/deseq2_model.nf').read_text().replace("'../../modules/cross_sample/deseq2'", repr(str(before / 'modules/cross_sample/deseq2'))))
            params = {'abundance': str(fixture / 'plasmids.tsv'), 'metadata': str(fixture / 'samples.tsv'),
                      'code_dir': str(before / 'bin' if old else ROOT / 'bin'), 'outdir': str(d / 'out'),
                      'publish_dir_mode': 'copy', 'min_group_replicates': minimum}
            if cross:
                params.update(fixture_dir=str(fixture), sample_ids=ids, samplesheet=str(fixture / 'samples.tsv'),
                              platform='illumina', run_diversity=False, min_diversity_samples=3,
                              run_differential_internal=False, run_differential_deseq2=True, run_network=False,
                              network_min_samples=20, project_name='controlled_DESeq2_contract', omit_state=False, duplicate_contig_table=False)
            case_state[name] = (d, fixture, ids, features, harness, params)
        inputs = {str(p.relative_to(fixture)): sha(p) for p in fixture.rglob('*') if p.is_file()}
        trace = d / (name + '.trace.tsv')
        pf = d / (name + '.params.json')
        pf.write_text(json.dumps(params))
        cmd = [shutil.which('nextflow') or 'nextflow', '-C', str(config), 'run', str(harness), '-params-file', str(pf),
               '-work-dir', str(d / 'work'), '-with-trace', str(trace), '-ansi-log', 'false'] + (['-resume'] if resume else [])
        result = subprocess.run(cmd, cwd=d, env=env, text=True, capture_output=True)
        (d / (name + '.console.log')).write_text(result.stdout + result.stderr)
        tasks = read(trace) if trace.exists() else []
        failure = name in ['before-positive', 'before-zero', 'invalid-min0', 'invalid-count', 'cross-invalid']
        assert (result.returncode != 0) == failure, (name, result.stdout + result.stderr)
        if failure:
            stderr = '\n'.join((Path(t['workdir']) / '.command.err').read_text() for t in tasks)
            needle = 'not parallel' if name == 'before-positive' else 'all samples have 0 counts' if name == 'before-zero' else 'coverage is not a count' if name == 'invalid-count' else '--min-replicates'
            assert needle in stderr, (name, stderr)
            assert any(t['status'] == 'FAILED' for t in tasks)
            assert not any(t['name'].split(' (')[0].endswith('REPORT') for t in tasks)
            assert not (d / 'out/report/report_data.json').exists()
            assert not (d / 'out/11_diversity/differential_plasmids.tsv').exists()
        else:
            output = d / 'out/11_diversity'
            actual = read(output / 'differential_plasmids.tsv')
            assert all(t['status'] in ['COMPLETED', 'CACHED'] for t in tasks)
            if old:
                assert name == 'before-two' and actual == []
            else:
                status = read(output / 'deseq2_status.tsv')
                assert len(status) == len(ids) and {r['sample_id'] for r in status} == set(ids)
                expected = expected_reasons.get(name, 'model_fitted')
                assert {r['reason'] for r in status} == {expected}, (name, status)
                assert {int(r['min_replicates']) for r in status} == {minimum}
                fitted = expected == 'model_fitted'
                assert {r['model_fitted'] for r in status} == {'TRUE' if fitted else 'FALSE'}
                if fitted:
                    assert {r['deseq2_version'] for r in status} == {'1.42.0'}
                    assert len(actual) == len(features) * (3 if kind == 'three' else 1)
                    if kind not in oracles:
                        oracle = base / ('oracle-' + kind + '.tsv')
                        ocmd = [str(prefix / 'bin/Rscript'), str(ROOT / 'tests/deseq2_reference.R'), str(fixture / 'wide.tsv'), str(fixture / 'samples.tsv'), str(oracle)]
                        ref = subprocess.run(ocmd, env=model_env, text=True, capture_output=True)
                        (base / ('oracle-' + kind + '.log')).write_text(ref.stdout + ref.stderr)
                        assert ref.returncode == 0, ref.stderr
                        oracles[kind] = {'command': ocmd, 'rows': read(oracle), 'sha256': sha(oracle)}
                    compare(actual, oracles[kind]['rows'])
                    if kind == 'ungrouped':
                        excluded = next(r for r in status if r['sample_id'] == ids[-1])
                        assert excluded['in_design'] == excluded['used_in_fit'] == 'FALSE' and excluded['model_library_size'] == ''
                else:
                    assert actual == [] and all(r['used_in_fit'] == 'FALSE' for r in status)
                if cross:
                    assert len(tasks) == 3
                    manifest = json.loads((d / 'out/report/report_inputs.json').read_text())
                    records = [r for r in manifest['records'] if r['producer'] == 'DESEQ2']
                    status_record = next(r for r in records if r['output'] == 'status')
                    model_task = next(t for t in tasks if t['name'].split(' (')[0].endswith('DESEQ2'))
                    # REPORTING retains completion evidence as paths; only
                    # detection files are staged for its counting summaries.
                    status_evidence = Path(status_record['evidence'])
                    assert status_evidence == Path(model_task['workdir']) / 'deseq2_status.tsv'
                    assert sha(status_evidence) == sha(output / 'deseq2_status.tsv')
                if name in ['positive-resume', 'cross-unchanged']: assert all(t['status'] == 'CACHED' for t in tasks)
                if name in ['positive-resume-raised', 'cross-raised']:
                    assert next(t for t in tasks if t['name'].split(' (')[0].endswith('DESEQ2'))['status'] == 'COMPLETED'
        assert inputs == {str(p.relative_to(fixture)): sha(p) for p in fixture.rglob('*') if p.is_file()}
        assert hashes == {n: sha(ROOT / n) for n in sources}
        runs.append({'case': name, 'command': cmd, 'exit': result.returncode, 'tasks': tasks, 'expected_failure': failure})
        (base / 'run.json').write_text(json.dumps({'pass': len(runs) == len(cases), 'expected_cases': len(cases),
            'runs': runs, 'source_sha256': hashes, 'oracles': {k: {x: v for x, v in d.items() if x != 'rows'} for k, d in oracles.items()},
            'limitations': ['native fixed1.42/R4.3 model; explicit synthetic counts/DNA/report inputs, not experimental differential accuracy',
                            'no image/remote executor/nf-test framework/full real P4 certification; no change to default estimator or read count units',
                            'before2rep case succeeds empty despite configured2; before positive/allzero failures retained',
                            'whole-design multi-group oracle uses the official API on separate wide input, not production importer/status code']}, indent=2) + '\n')
        print('PASS', name, len(tasks), 'trace entries', flush=True)


if __name__ == '__main__':
    main()
