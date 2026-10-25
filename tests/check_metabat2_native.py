#!/usr/bin/env python3
"""Independent fixed-fixture membership/DNA/depth oracle; no MAG-quality claim."""
import argparse
from collections import defaultdict
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def fasta(path):
    result = {}
    with gzip.open(path, 'rt') as stream:
        for line in stream:
            if line.startswith('>'):
                name = line[1:].split()[0]
                assert name not in result, 'Duplicate FASTA ID'
                result[name] = ''
            elif line.strip():
                assert result
                result[name] += line.strip()
    assert result and all(result.values())
    return result


def check(fixture, products, mode):
    lock = json.loads((ROOT / 'tests/nf-test/real-nodes-datasets.lock.json').read_text())
    for name in ['contigs.fasta.gz', 's1.sorted.bam', 's1.sorted.bam.bai']:
        expected = next(row for row in lock['files'] if row.get('path', '').endswith('/binning/multisample/' + name))
        data = (fixture / name).read_bytes()
        assert len(data) == expected['size']
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == expected['git_blob_sha1'], 'Fixed fixture identity differs'
    source = fasta(fixture / 'contigs.fasta.gz')
    with gzip.open(products / 'depth/binning_s1.txt.gz', 'rt') as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        assert reader.fieldnames == ['contigName', 'contigLen', 'totalAvgDepth', 's1.sorted', 's1.sorted-var']
        rows = list(reader)
    assert len(rows) == len(source)
    depth = {row['contigName']: row for row in rows}
    assert set(depth) == set(source)
    for key, row in depth.items():
        assert int(row['contigLen']) == len(source[key])
        assert all(math.isfinite(float(row[column])) and float(row[column]) >= 0 for column in ['totalAvgDepth', 's1.sorted', 's1.sorted-var'])
    with gzip.open(products / 'binning_s1.tsv.gz', 'rt') as stream:
        membership = list(csv.reader(stream, delimiter='\t'))
    assert membership and all(len(row) == 2 and row[0] in source and re.fullmatch(r'[0-9]+', row[1]) for row in membership)
    assert len({row[0] for row in membership}) == len(membership)
    declared = defaultdict(set)
    for contig, label in membership:
        if label != '0':
            declared[label].add(contig)
    emitted, seen = {}, set()
    for path in products.glob('*.fa.gz'):
        match = re.fullmatch(r'binning_s1\.([0-9]+)\.fa\.gz', path.name)
        assert match, 'Unexpected auxiliary/output FASTA in this fixture'
        dna = fasta(path)
        assert not seen.intersection(dna), 'Contig emitted more than once'
        assert all(key in source and value == source[key] for key, value in dna.items()), 'Foreign ID or changed bin DNA'
        seen.update(dna)
        emitted[match[1]] = set(dna)
    # Fixed upstream2.17 output_bins() uses internal cluster key+1 in the
    # matrix, and an independent sequential bin_id in FASTA filenames.
    # Compare the complete partitions; those two numeric labels can differ.
    declared_partition = {frozenset(members) for members in declared.values()}
    emitted_partition = {frozenset(members) for members in emitted.values()}
    assert len(emitted) == len(declared) and emitted_partition == declared_partition, 'Membership partition and emitted bins disagree'
    if mode == 'default-empty':
        eligible = {key for key, row in depth.items() if len(source[key]) >= 2500 and float(row['totalAvgDepth']) >= 1}
        # The maximum eligible DNA is smaller than the declared 200kb bin
        # minimum. This predicts zero bins independently of the first run.
        assert 0 < sum(len(source[key]) for key in eligible) < 200000
        assert not emitted and {row[0] for row in membership} == eligible
    else:
        assert emitted and seen, 'Upstream permissive settings must exercise nonempty bin publication'
        assert all(len(source[key]) >= 1500 and float(depth[key]['totalAvgDepth']) >= .1 for key in seen)
    return {'pass': True, 'mode': mode, 'source_contigs': len(source), 'depth_rows': len(rows),
            'membership_rows': len(membership), 'bins': len(emitted), 'binned_contigs': len(seen),
            'binned_bases': sum(len(source[key]) for key in seen),
            'scope': 'Fixed upstream software fixture, depth domain/length/finite values and exact membership/DNA. Permissive settings are upstream test parameters, not production defaults or independent MAG-quality truth.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--products', type=Path, required=True)
    parser.add_argument('--mode', choices=['default-empty', 'upstream-nonempty'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = check(args.fixture, args.products, args.mode)
    result['source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print('PASS independent MetaBAT2 DNA/membership/depth oracle;', result['bins'], 'bins')


if __name__ == '__main__':
    main()
