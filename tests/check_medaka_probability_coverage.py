#!/usr/bin/env python3
"""Check real neural probability coverage independently of draft gap filling."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-reference', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    import numpy as np
    from medaka.datastore import DataStore
    base = args.native_reference.resolve()
    result = json.loads((base / 'run.json').read_text())
    assert result['pass_native_computation_checks']
    lengths = result['draft_sequence_lengths']
    masks = {name: np.zeros(length, dtype=bool) for name, length in lengths.items()}
    row_count = 0
    sum_min, sum_max = float('inf'), float('-inf')
    hdf = base / 'native/consensus_probs.hdf'
    with DataStore(str(hdf), 'r') as store:
        names = sorted(store.sample_registry)
        assert names
        for name in names:
            sample = store.load_sample(name)
            assert sample.ref_name in masks
            probabilities = sample.label_probs
            assert probabilities.ndim == 2 and probabilities.shape[1] == 5
            assert len(probabilities) == len(sample.positions) > 0
            assert np.isfinite(probabilities).all()
            assert (probabilities >= 0).all() and (probabilities <= 1).all()
            sums = probabilities.sum(axis=1)
            assert np.allclose(sums, 1, atol=0.001, rtol=0)
            sum_min = min(sum_min, float(sums.min()))
            sum_max = max(sum_max, float(sums.max()))
            major = np.unique(sample.positions['major'])
            assert (major >= 0).all() and (major < lengths[sample.ref_name]).all()
            masks[sample.ref_name][major] = True
            row_count += len(probabilities)
    coverage = {name: {'draft_length': lengths[name], 'unique_neural_major_positions': int(mask.sum()),
                       'fraction': float(mask.mean())} for name, mask in masks.items()}
    # Deduplicate overlapping chunks/insertions. BAM coverage and output FASTA
    # presence cannot establish that neural probabilities covered the draft.
    assert all(row['fraction'] > 0.95 for row in coverage.values()), coverage
    root = Path(__file__).resolve().parents[1]
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    report = {'pass_full_neural_coverage_checks': True, 'formal_acceptance': False,
              'source_sha256': {str(Path(__file__).resolve().relative_to(root)): sha(Path(__file__))},
              'native_run_sha256': sha(base / 'run.json'), 'hdf_sha256': sha(hdf),
              'probability_rows_including_overlaps_and_insertions': row_count,
              'hdf_samples': len(names), 'row_sum_min': sum_min, 'row_sum_max': sum_max,
              'unique_major_position_coverage': coverage,
              'scope': 'Actual native HDF probabilities, finite/normalized 5-class rows and >95% unique major-position neural coverage for every draft contig. Independent of BAM coverage and draft gap filling; not a biological error-rate or genome-truth benchmark.'}
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2) + '\n')
    print(json.dumps(coverage))


if __name__ == '__main__':
    main()
