#!/usr/bin/env python3
"""Calibrate a TETRA candidate cutoff on explicitly labeled, disjoint cohorts.

Labels are curator assertions with evidence, not inferred from absent host links.
This does not establish host permissiveness or certify a dataset's provenance.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

METHOD = 'tetra_markov256_v1'
KEYS = ['sample_id', 'plasmid_id', 'host_id']


def rows(path):
    with path.open() as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        if reader.fieldnames is None: raise ValueError(f'Empty table: {path}')
        return list(reader)


def load_labels(path):
    records = rows(path); seen = set(); groups = {'calibration': [set(), set()], 'holdout': [set(), set()]}
    for row in records:
        required = KEYS + ['label', 'split', 'plasmid_group', 'host_group', 'label_evidence']
        if any(not row.get(k, '').strip() for k in required): raise ValueError('Labels need explicit IDs, binary label, split, both grouping IDs and label_evidence')
        key = tuple(row[k] for k in KEYS)
        if key in seen: raise ValueError('Duplicate labeled pair')
        seen.add(key)
        if row['label'] not in ['0', '1'] or row['split'] not in groups: raise ValueError('Invalid label/split')
        row['label'] = int(row['label'])
        for i, key in enumerate(['plasmid_group', 'host_group']): groups[row['split']][i].add(row[key])
    for i in [0, 1]:
        if groups['calibration'][i] & groups['holdout'][i]: raise ValueError('Calibration/holdout group leakage (plasmid or host)')
    # Exact IDs must also not bypass the grouping barrier with invented group names.
    for key in ['plasmid_id', 'host_id']:
        # These IDs are local to a sample. Shared sequence/lineage identity is
        # represented by the required curator group IDs above.
        if {(r['sample_id'], r[key]) for r in records if r['split'] == 'calibration'} & {(r['sample_id'], r[key]) for r in records if r['split'] == 'holdout'}:
            raise ValueError('Calibration/holdout entity leakage')
    for split in groups:
        if {r['label'] for r in records if r['split'] == split} != {0, 1}: raise ValueError('Both labels are required in each cohort')
    return records


def load_scores(paths):
    result = {}
    for path in paths:
        for row in rows(path):
            if any(not row.get(k) for k in KEYS) or row.get('method') != METHOD: raise ValueError('Score identity/method mismatch')
            key = tuple(row[k] for k in KEYS)
            if key in result: raise ValueError('Duplicate scored pair')
            if row.get('profile_status') == 'complete256':
                value = float(row['score'])
                if not math.isfinite(value) or not -1 <= value <= 1: raise ValueError('Invalid Pearson score')
            elif row.get('profile_status') == 'ineligible_profile' and row.get('score', '') == '': value = None
            else: raise ValueError('Invalid score/profile state')
            result[key] = value
    return result


def metrics(records, threshold):
    available = [r for r in records if r['score'] is not None]
    tp = sum(r['label'] == 1 and r['score'] >= threshold for r in available)
    fp = sum(r['label'] == 0 and r['score'] >= threshold for r in available)
    tn = sum(r['label'] == 0 and r['score'] < threshold for r in available)
    fn = sum(r['label'] == 1 and r['score'] < threshold for r in available)
    sensitivity = tp / (tp + fn) if tp + fn else None
    specificity = tn / (tn + fp) if tn + fp else None
    return {'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn,
        'precision': tp / (tp + fp) if tp + fp else None, 'sensitivity': sensitivity,
        'specificity': specificity,
        'balanced_accuracy': (sensitivity + specificity) / 2 if sensitivity is not None and specificity is not None else None,
        'labeled_pairs': len(records), 'eligible_pairs': len(available),
        'ineligible_by_label': {str(label): sum(r['label'] == label and r['score'] is None for r in records) for label in [0, 1]},
        'metric_scope': 'eligible pairs only; ineligible profiles abstain and are reported separately, not true negatives'}


def calibrate(score_paths, label_path, endpoint, minimum_precision):
    if not 0 < minimum_precision <= 1: raise ValueError('Minimum calibration precision must be in (0,1]')
    labels = load_labels(label_path); scores = load_scores(score_paths)
    for row in labels:
        key = tuple(row[k] for k in KEYS)
        if key not in scores: raise ValueError('Missing scored pair; use unfiltered all-pairs sequence_scores.tsv, not selected links')
        row['score'] = scores[key]
    train = [r for r in labels if r['split'] == 'calibration']; holdout = [r for r in labels if r['split'] == 'holdout']
    # Threshold policy is restricted to the production parameter domain [0,1].
    thresholds = sorted({0., 1.} | {r['score'] for r in train if r['score'] is not None and r['score'] >= 0})
    candidates = [{'threshold': t, **metrics(train, t)} for t in thresholds]
    feasible = [c for c in candidates if c['precision'] is not None and c['precision'] >= minimum_precision and c['balanced_accuracy'] is not None]
    selected = max(feasible, key=lambda c: (c['balanced_accuracy'], c['specificity'], c['threshold'])) if feasible else None
    return {'method': METHOD, 'endpoint': endpoint, 'status': 'estimated_on_supplied_labels' if selected else 'no_feasible_cutoff',
        'selection': 'calibration only: maximize eligible balanced accuracy subject to minimum precision; tie specificity then higher cutoff',
        'minimum_calibration_precision': minimum_precision, 'selected_threshold': selected['threshold'] if selected else None,
        'calibration': selected, 'holdout': metrics(holdout, selected['threshold']) if selected else None,
        'calibration_candidates': candidates,
        'inputs_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [label_path, *score_paths]},
        'label_provenance': 'Supplied curator labels/evidence; not independently verified by this numerical tool',
        'labels': labels,
        'limitations': ['Cutoff not automatically installed into pipeline; independent holdout performance/coverage and label provenance require scientific review.',
            'An assembly-of-isolation endpoint does not imply experimental host range or true non-permissiveness of decoys.',
            'A fixture/small or biased panel cannot establish generalizable biological performance.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scores', nargs='+', required=True, type=Path)
    parser.add_argument('--labels', required=True, type=Path)
    parser.add_argument('--endpoint', required=True, choices=['recorded_assembly_host', 'experimental_permissiveness'])
    parser.add_argument('--min-calibration-precision', type=float, default=.9)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try: result = calibrate(args.scores, args.labels, args.endpoint, args.min_calibration_precision)
    except (ValueError, KeyError) as error: parser.error(str(error))
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return 0 if result['selected_threshold'] is not None else 2


if __name__ == '__main__': raise SystemExit(main())
