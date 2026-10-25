#!/usr/bin/env python3
"""Independently verify a completed full PlasX workflow; never infer accuracy from it.

Uses only the standard library for family counts and logistic arithmetic. The
optional original CLI comparison executes the locked upstream source, not an
observer. This is a verifier of an existing execution, not a new search run.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def rows(path):
    with Path(path).open() as stream:
        return list(csv.DictReader(stream, delimiter='\t'))


def families(genes, annotations, contig_map=None):
    """Count every annotation occurrence, including !!! multi-accessions.

    The upstream sparse matrix sums repeated entries; a set of families or a
    binary presence matrix would silently change the fitted model's inputs.
    """
    gene_map = {row['gene_callers_id']: row['contig'] for row in genes}
    assert len(gene_map) == len(genes), 'Duplicate gene IDs'
    result = defaultdict(Counter)
    for table in annotations:
        for row in table:
            contig = row.get('contig') or gene_map[row['gene_callers_id']]
            assert contig == gene_map[row['gene_callers_id']], 'Foreign annotation contig'
            if contig_map is not None:
                contig = contig_map[contig]
            for accession in row['accession'].split('!!!'):
                assert accession, 'Empty annotation accession'
                result[contig][accession] += 1
    return dict(result)


def probabilities(counts, model):
    wanted = set().union(*(set(value) for value in counts.values())) if counts else set()
    coefficients = {}
    intercept = None
    with Path(model).open() as stream:
        for row in csv.DictReader(stream, delimiter='\t'):
            feature = row['accession']
            if feature == 'INTERCEPT':
                assert intercept is None, 'Duplicate intercept'
                intercept = float(row['PlasX_coefficient'])
            elif feature in wanted:
                assert feature not in coefficients, 'Duplicate coefficient'
                coefficients[feature] = float(row['PlasX_coefficient'])
    assert intercept is not None and math.isfinite(intercept)
    assert all(math.isfinite(value) for value in coefficients.values())
    values = {}
    for contig, observed in counts.items():
        z = math.fsum([intercept] + [n * coefficients.get(feature, 0.0) for feature, n in observed.items()])
        values[contig] = 1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))
    return values


def compare_scores(expected, actual):
    assert set(actual) == set(expected), 'Score contig domain differs'
    assert all(math.isfinite(value) and 0 <= value <= 1 for value in actual.values())
    error = max((abs(actual[key] - value) for key, value in expected.items()), default=0)
    assert error <= 1e-12, ('Logistic score differs', error)
    return error


def scores(path):
    table = rows(path)
    result = {row['contig']: float(row['score']) for row in table}
    assert len(result) == len(table), 'Duplicate scored contig'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    location = parser.add_mutually_exclusive_group(required=True)
    location.add_argument('--workflow', type=Path, help='Recorded complete cold workflow, including source and trace receipt')
    location.add_argument('--products', type=Path, help='Published products only; caller must separately verify actual execution')
    for name in ['model', 'output', 'source']:
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--sample', default='S.1')
    parser.add_argument('--prefix', type=Path, help='Optional native prefix for unmodified upstream predict')
    args = parser.parse_args()
    lock = json.loads((ROOT / 'tests/plasx-native.lock.json').read_text())
    assert sha(args.model) == lock['model_sha256'], 'Original full model identity differs'
    for name, expected in lock['official_fixture_sha256'].items():
        assert sha(args.source / 'test' / name) == expected, 'Official fixture identity differs: ' + name
    base = args.output.resolve()
    base.mkdir(exist_ok=False)
    execution_sources = {}
    execution_inputs = []
    if args.workflow:
        workflow = args.workflow.resolve()
        execution = json.loads((workflow / 'execution.json').read_text())
        assert execution['exit_code'] == 0 and execution['source_unchanged']
        execution_sources = execution['source_sha256']
        assert all(sha(ROOT / path) == value for path, value in execution_sources.items()), 'Execution source changed'
        trace = rows(workflow / 'trace.tsv')
        assert len(trace) == 2 and all(row['status'] == 'COMPLETED' and row['exit'] == '0' for row in trace)
        assert {row['name'].split(' (')[0] for row in trace} == {'PLASX_ANNOTATE', 'PLASX'}
        out = workflow / 'out/04_plasmid_detection/plasx'
        execution_inputs = [workflow / 'execution.json', workflow / 'trace.tsv']
    else:
        out = args.products.resolve()
    sample = args.sample
    paths = {key: out / (sample + '.' + key + '.tsv') for key in ['gene_calls', 'cogs_pfams', 'de_novo', 'id_map', 'plasx', 'plasx_state']}
    genes = rows(paths['gene_calls'])
    mapping = rows(paths['id_map'])
    assert all(row['sample_id'] == sample for row in mapping)
    names = {row['contig']: row['original_contig'] for row in mapping}
    assert len(names) == len(mapping) == len(set(names.values()))
    counts = families(genes, [rows(paths['cogs_pfams']), rows(paths['de_novo'])], names)
    actual = scores(paths['plasx'])
    error = compare_scores(probabilities(counts, args.model), actual)
    states = rows(paths['plasx_state'])
    assert len(states) == len(names) and {row['contig'] for row in states} == set(names.values())
    gene_contigs = {names[row['contig']] for row in genes}
    for row in states:
        expected = 'scored' if row['contig'] in counts else 'not_assessed_no_annotations' if row['contig'] in gene_contigs else 'not_assessed_no_genes'
        assert row['sample_id'] == sample and row['status'] == expected
    original = None
    if args.prefix:
        output = base / 'original-current-scores.tsv'
        command = [str(args.prefix.resolve() / 'bin/python'), '-c', 'from plasx.plasx_script import run; run()', 'predict',
                   '-a', str(paths['cogs_pfams']), str(paths['de_novo']), '-g', str(paths['gene_calls']),
                   '-m', str(args.model.resolve()), '-o', str(output)]
        env = dict(os.environ, PYTHONPATH=str(args.source.resolve()), PYTHONDONTWRITEBYTECODE='1')
        with (base / 'original.stdout.log').open('w') as stdout, (base / 'original.stderr.log').open('w') as stderr:
            process = subprocess.run(command, cwd=base, env=env, stdout=stdout, stderr=stderr)
        original = {'command': command, 'exit_code': process.returncode}
        assert process.returncode == 0, original
        restored = {names[key]: value for key, value in scores(output).items()}
        original['maximum_absolute_difference'] = compare_scores(actual, restored)
    official = args.source / 'test'
    old_counts = families(rows(official / 'test-contigs-gene-calls.txt'), [rows(official / 'test-contigs-cogs-and-pfams.txt'), rows(official / 'test-contigs-de-novo-families.txt')])
    official_scores = scores(official / 'test-contigs-scores.txt')
    official_error = compare_scores(probabilities(old_counts, args.model), official_scores)
    difference = []
    for contig in sorted(set(counts) | set(old_counts)):
        old, new = old_counts.get(contig, Counter()), counts.get(contig, Counter())
        changed = {key: {'official_precomputed': old[key], 'automatic': new[key]} for key in old.keys() | new.keys() if old[key] != new[key]}
        if changed:
            difference.append({'contig': contig, 'family_counts_changed': changed, 'official_score': official_scores.get(contig), 'automatic_score': actual.get(contig)})
    (base / 'annotation-differences.json').write_text(json.dumps(difference, indent=2) + '\n')
    result = {'pass': True, 'scope': ('recorded cold source/trace and products' if args.workflow else 'products only; actual execution must be checked separately') + '; independent stdlib count/logistic arithmetic, optional new original predict; no new full search or biological accuracy claim',
              'genes': len(genes), 'cog_pfam_rows': len(rows(paths['cogs_pfams'])), 'de_novo_rows': len(rows(paths['de_novo'])), 'scored_contigs': len(actual),
              'state_counts': Counter(row['status'] for row in states), 'score_maximum_absolute_difference': error, 'official_fixture_arithmetic_error': official_error,
              'strict_half_positive_counts': {'automatic': sum(value > .5 for value in actual.values()), 'official_precomputed': sum(value > .5 for value in official_scores.values())},
              'contigs_with_changed_family_counts': len(difference), 'original_current_predict': original,
              'source_sha256': {'tests/run_plasx_native.py': sha(__file__), 'tests/plasx-native.lock.json': sha(ROOT / 'tests/plasx-native.lock.json'), **execution_sources},
              'input_sha256': {str(path): sha(path) for path in [args.model, *execution_inputs, *paths.values()]}}
    (base / 'run.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ['pass', 'genes', 'scored_contigs', 'score_maximum_absolute_difference', 'strict_half_positive_counts', 'contigs_with_changed_family_counts']}))


if __name__ == '__main__':
    main()
