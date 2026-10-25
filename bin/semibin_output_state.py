#!/usr/bin/env python3
"""Record the final, post-filter SemiBin 2.4.1 bin state without inventing bins."""
import argparse
import csv
import json
from pathlib import Path


FIELDS = ['filename', 'nbps', 'nr_contigs', 'N50', 'L50']


def record_state(output):
    output = Path(output)
    directory = output/'output_bins'
    if not directory.is_dir():
        raise ValueError('Missing SemiBin output_bins directory')
    bins = sorted(directory.iterdir())
    if any(not p.is_file() or not p.name.endswith('.fa.gz') or p.stat().st_size == 0 for p in bins):
        raise ValueError('Expected nonempty SemiBin default-compression .fa.gz bin files')
    # contig_bins.tsv describes labels before final size filtering/reclustering;
    # it is not a roster of the FASTAs actually retained in output_bins.
    summary = output/'recluster_bins_info.tsv'
    with summary.open(newline='') as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        if reader.fieldnames != FIELDS:
            raise ValueError('Unexpected SemiBin final bin summary header')
        rows = list(reader)
    paths = {}
    for row in rows:
        if set(row) != set(FIELDS) or any(row[k] is None for k in FIELDS):
            raise ValueError('Malformed SemiBin final bin summary row')
        path = Path(row['filename']).resolve()
        if path in paths:
            raise ValueError('Duplicate SemiBin final bin summary entry')
        metrics = {k: int(row[k]) for k in FIELDS[1:]}
        if any(v <= 0 for v in metrics.values()):
            raise ValueError('Invalid SemiBin final bin summary metrics')
        paths[path] = metrics
    if set(paths) != {p.resolve() for p in bins}:
        raise ValueError('SemiBin final summary and output FASTA sets differ')
    state = {'schema': 1, 'state': 'bins_ready' if bins else 'no_bins',
             'bin_count': len(bins),
             'bins': [{'filename': p.name, **paths[p.resolve()]} for p in bins],
             'scope': 'final output_bins after filtering and reclustering; not quality-controlled MAGs'}
    destination = output/'binning_status.json'
    if destination.exists():
        raise ValueError('SemiBin binning status already exists')
    destination.write_text(json.dumps(state, indent=2)+'\n')
    return state


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    record_state(parser.parse_args().output)
