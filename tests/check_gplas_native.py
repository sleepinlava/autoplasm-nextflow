#!/usr/bin/env python3
"""Independent final graph-node/DNA/membership check; no production helper import."""
import argparse
from collections import defaultdict
import csv
import hashlib
from itertools import groupby
import json
import math
from pathlib import Path


def graph_records(path):
    source, edges = {}, []
    with Path(path).open() as stream:
        for line in stream:
            cells = line.rstrip('\n').split('\t')
            if cells[0] == 'S':
                assert cells[1] not in source
                source[cells[1]] = ('S' + cells[1] + '_' + cells[3] + '_' + (cells[4] if len(cells) > 4 else ''), cells[2].upper())
            elif cells[0] == 'L':
                edges.append(tuple(cells[1:6]))
    assert source
    return source, sorted(edges)


def check(graph, products, name, input_graph=None):
    source, edges = graph_records(graph)
    if input_graph is not None:
        native, native_edges = graph_records(input_graph)
        assert {k: v[1] for k, v in native.items()} == {k: v[1] for k, v in source.items()}, 'Normalized graph changed node DNA/domain'
        assert native_edges == edges, 'Normalized graph changed edges'
        source = native
    products = Path(products)
    with (products / (name + '_results.tab')).open() as stream:
        rows = list(csv.DictReader(stream, delimiter=' '))
    assert rows, 'No native positive membership'
    members, groups = set(), defaultdict(dict)
    for row in rows:
        ident, sequence = source[row['number']]
        assert row['Contig_name'] == ident and int(row['length']) == len(sequence)
        for key in ['Prob_Chromosome', 'Prob_Plasmid', 'coverage']:
            assert math.isfinite(float(row[key])) and float(row[key]) >= 0
        key = (row['number'], row['Bin'])
        assert key not in members
        members.add(key)
        groups[row['Bin']][ident] = sequence
    with (products / (name + '_bins.tab')).open() as stream:
        ids = [(r['number'], r['Bin']) for r in csv.DictReader(stream, delimiter=' ')]
    assert len(ids) == len(set(ids)) and set(ids) == members
    hashes = {}
    for group, expected in groups.items():
        file = products / (name + '_bin_' + group + '.fasta')
        observed = {}
        with file.open() as stream:
            chunks = groupby((line.strip() for line in stream if line.strip()), key=lambda x: x.startswith('>'))
            for is_header, lines in chunks:
                assert is_header
                names = list(lines)
                assert len(names) == 1
                ident = names[0][1:]
                assert ident not in observed
                flag, dna = next(chunks)
                assert not flag
                observed[ident] = ''.join(dna).upper()
        assert observed == expected, 'Foreign or incomplete bin DNA: ' + group
        hashes[file.name] = hashlib.sha256(file.read_bytes()).hexdigest()
    assert {p.name for p in products.glob(name + '_bin_*.fasta')} == set(hashes)
    return {'pass': True, 'memberships': len(members), 'fasta_groups': len(groups),
            'original_graph_sha256': hashlib.sha256(Path(graph).read_bytes()).hexdigest(),
            'native_input_graph_sha256': hashlib.sha256(Path(input_graph or graph).read_bytes()).hexdigest(),
            'candidate_bins': sum(g not in ['Unbinned', 'Repeat_like'] for g in groups),
            'fasta_sha256': hashes, 'scope': 'native result identity and DNA against original graph; not biological accuracy'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ['graph', 'products', 'name', 'output']:
        parser.add_argument('--' + key, required=True)
    parser.add_argument('--input-graph', help='Optional normalized native GFA; verify its entire DNA/domain/edges against --graph first')
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(check(args.graph, args.products, args.name, args.input_graph), indent=2) + '\n')
