#!/usr/bin/env python3
"""Prepare SPAdes graph nodes and typed consensus decisions for fixed gplas.

The original gplas parser reads positional GFA tags. SPAdes4 emits DP then
KC; its coverage code needs KC as the sole node tag. Keep the original KC
count, node sequence and edges, and record every resulting header explicitly.
"""
import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import statistics


HEADER = ['Prob_Chromosome', 'Prob_Plasmid', 'Prediction', 'Contig_name', 'Contig_length']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def graph_nodes(source, minimum=1000):
    if minimum != 1000:
        raise ValueError('This adapter preserves the upstream default minimum length of 1000')
    raw = Path(source).read_bytes()
    text = (gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw).decode('utf-8')
    nodes, edges = {}, []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line or line.startswith('#'):
            continue
        fields = line.split('\t')
        if fields[0] == 'H':
            continue
        if fields[0] == 'S':
            if len(fields) < 4 or not re.fullmatch(r'[0-9]+', fields[1]):
                raise ValueError('Expected numeric SPAdes GFA segment ID at line %d' % lineno)
            node, dna = fields[1:3]
            if node in nodes:
                raise ValueError('Duplicate graph segment: ' + node)
            if not dna or not re.fullmatch(r'[ACGTRYSWKMBDHVNacgtryswkmbdhvn]+', dna):
                raise ValueError('Graph must contain explicit nucleotide sequences: ' + node)
            tags = {}
            for tag in fields[3:]:
                parts = tag.split(':', 2)
                if len(parts) != 3 or parts[0] in tags:
                    raise ValueError('Invalid or duplicate GFA tag: ' + node)
                tags[parts[0]] = parts[1:]
            if 'KC' not in tags or tags['KC'][0] != 'i' or not re.fullmatch(r'[0-9]+', tags['KC'][1]):
                raise ValueError('SPAdes graph segment requires nonnegative KC:i count: ' + node)
            if 'LN' in tags and tags['LN'] != ['i', str(len(dna))]:
                raise ValueError('GFA length tag differs from sequence: ' + node)
            if 'DP' in tags:
                depth = float(tags['DP'][1])
                if tags['DP'][0] != 'f' or not math.isfinite(depth) or depth < 0:
                    raise ValueError('Invalid SPAdes DP depth: ' + node)
            kc = int(tags['KC'][1])
            # Exact header produced by fixed upstream awk for this normalized S line.
            header = 'S%s_KC:i:%d_' % (node, kc)
            nodes[node] = {'node_id': node, 'header': header, 'dna': dna,
                           'length': len(dna), 'kc': kc, 'original_tags': fields[3:],
                           'classified': len(dna) >= minimum}
        elif fields[0] == 'L':
            if len(fields) != 6 or fields[2] not in ['+', '-'] or fields[4] not in ['+', '-']:
                raise ValueError('Expected six-column oriented GFA link at line %d' % lineno)
            if not re.fullmatch(r'(?:[0-9]+[MIDNSHP=X])+', fields[5]):
                raise ValueError('Invalid GFA link overlap at line %d' % lineno)
            edges.append(fields)
        elif fields[0] in ['P', 'W']:
            # gplas uses segment/link records, never assembled-contig paths.
            continue
        else:
            raise ValueError('Unsupported graph record for gplas: ' + fields[0])
    if not nodes:
        raise ValueError('Graph has no segments')
    for edge in edges:
        if edge[1] not in nodes or edge[3] not in nodes:
            raise ValueError('Graph link refers to missing segment')
    if statistics.median(v['kc'] / v['length'] for v in nodes.values()) <= 0:
        raise ValueError('Graph has no positive median k-mer coverage')
    return nodes, edges


def prepare(source, prefix, sample_id):
    nodes, edges = graph_nodes(source)
    graph, fasta, state = [Path(str(prefix) + suffix) for suffix in
                           ['.gplas.gfa', '.gplas_nodes.fasta', '.gplas_nodes.json']]
    if any(p.exists() for p in [graph, fasta, state]):
        raise ValueError('Refusing to replace existing graph-node products')
    with graph.open('w') as out:
        out.write('H\tVN:Z:1.0\n')
        for node in nodes.values():
            out.write('S\t%s\t%s\tKC:i:%d\n' % (node['node_id'], node['dna'], node['kc']))
        for edge in edges:
            out.write('\t'.join(edge) + '\n')
    with fasta.open('w') as out:
        for node in nodes.values():
            if node['classified']:
                out.write('>%s\n%s\n' % (node['header'], node['dna']))
    manifest = {'sample_id': sample_id, 'original_graph_sha256': sha(source),
                'normalized_graph_sha256': sha(graph), 'node_fasta_sha256': sha(fasta),
                'minimum_length': 1000, 'total_nodes': len(nodes), 'links': len(edges),
                'classified_nodes': sum(v['classified'] for v in nodes.values()),
                'coverage_adapter': 'fixed gplas SPAdes KC/sequence-length normalized by median; original DP retained as provenance only',
                'state': 'nodes_ready' if fasta.stat().st_size else 'not_assessed_length_filter',
                'nodes': [{k: v for k, v in n.items() if k != 'dna'} for n in nodes.values()]}
    state.write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def predictions(graph, consensus, output, sample_id, classified_sample_id, assessment):
    nodes, _ = graph_nodes(graph)
    expected = {n['header']: n for n in nodes.values() if n['classified']}
    assessed = set()
    with Path(assessment).open(newline='') as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        if reader.fieldnames != ['seq_name', 'chromosome_score', 'plasmid_score', 'virus_score']:
            raise ValueError('Expected original-node geNomad aggregated classification table')
        for row in reader:
            cid = row['seq_name']
            if cid not in expected or cid in assessed:
                raise ValueError('Foreign or duplicate geNomad assessment node: ' + cid)
            scores = [float(row[key]) for key in reader.fieldnames[1:]]
            if not all(math.isfinite(v) and 0 <= v <= 1 for v in scores) or abs(sum(scores) - 1) > 0.001:
                raise ValueError('Invalid original-node geNomad classification scores')
            assessed.add(cid)
    if assessed != set(expected):
        raise ValueError('Graph nodes were not all assessed; cannot encode missing evaluation as a chromosome decision')
    with Path(consensus).open(newline='') as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        required = {'contig_id', 'sample_id', 'plasmid_call', 'length'}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError('Expected complete graph-node consensus table')
        rows = list(reader)
    calls = {}
    for row in rows:
        cid = row['contig_id']
        if cid not in expected or cid in calls:
            raise ValueError('Unexpected or duplicate classified graph node: ' + cid)
        if row['sample_id'] != classified_sample_id:
            raise ValueError('Graph-node consensus belongs to another sample')
        if row['plasmid_call'] not in ['plasmid', 'chromosome']:
            raise ValueError('Unassessed graph node cannot become a chromosome decision')
        if row['length'] != str(expected[cid]['length']):
            raise ValueError('Classified graph-node length differs from source: ' + cid)
        calls[cid] = row['plasmid_call']
    if set(calls) != set(expected):
        raise ValueError('Graph-node consensus is incomplete')
    output = Path(output)
    if output.exists() or output.with_suffix('.state.json').exists():
        raise ValueError('Refusing to replace prediction products')
    with output.open('w', newline='') as stream:
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        writer.writerow(HEADER)
        for cid, node in expected.items():
            call = calls[cid] == 'plasmid'
            writer.writerow([int(not call), int(call), 'Plasmid' if call else 'Chromosome', cid, node['length']])
    positives = sum(v == 'plasmid' for v in calls.values())
    state = {'sample_id': sample_id, 'classified_sample_id': classified_sample_id,
             'graph_sha256': sha(graph), 'consensus_sha256': sha(consensus),
             'genomad_assessment_sha256': sha(assessment), 'assessed_nodes': len(assessed),
             'predictions_sha256': sha(output), 'classified_nodes': len(calls),
             'plasmid_seeds': positives, 'not_assessed_length_filter': len(nodes) - len(expected),
             'state': 'ready' if positives else 'no_plasmid_seeds' if expected else 'not_assessed_length_filter',
             'encoding': 'one-hot encoding of consensus decisions accepted by gplas; not calibrated probabilities or independent chromosome identification'}
    output.with_suffix('.state.json').write_text(json.dumps(state, indent=2) + '\n')
    return state


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    prep = sub.add_parser('prepare')
    for key in ['graph', 'prefix', 'sample-id']:
        prep.add_argument('--' + key, required=True)
    pred = sub.add_parser('predictions')
    for key in ['graph', 'consensus', 'output', 'sample-id', 'classified-sample-id', 'genomad-assessment']:
        pred.add_argument('--' + key, required=True)
    args = parser.parse_args()
    if args.mode == 'prepare':
        prepare(args.graph, args.prefix, args.sample_id)
    else:
        state = predictions(args.graph, args.consensus, args.output, args.sample_id, args.classified_sample_id, args.genomad_assessment)
        if state['plasmid_seeds']:
            Path(args.output + '.ready').touch()
