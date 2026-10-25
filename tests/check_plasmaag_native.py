#!/usr/bin/env python3
"""Independently validate fixed native PlasMAAG products against original assemblies."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path


def fasta(path):
    records = {}; name = None
    with Path(path).open() as stream:
        for line in stream:
            if line.startswith('>'):
                name = line[1:].split()[0]
                assert name not in records, ('duplicate FASTA ID', path, name)
                records[name] = ''
            elif line.strip():
                assert name is not None
                records[name] += line.strip().upper()
    return records


def check(manifest, products):
    with Path(manifest).open() as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        assert reader.fieldnames == ['read1', 'read2', 'assembly_dir']
        samples = list(reader)
    assert samples
    reference = {}; sample_map = {}
    for index, row in enumerate(samples):
        original = Path(row['assembly_dir']) / 'contigs.fasta'
        records = fasta(original); assert records
        prefix = 'S' + str(index) + 'C'
        reference.update({prefix + name: sequence for name, sequence in records.items()})
        sample_map[prefix] = dict(assembly=str(original), sha256=hashlib.sha256(original.read_bytes()).hexdigest(), contigs=len(records))
    products = Path(products); counts = {}; hashes = {}; all_classified = set()
    for category, minimum in [('candidate_plasmids', 1), ('candidate_genomes', 200000), ('candidate_virus', 1)]:
        table = products / (category + '.tsv')
        with table.open() as stream:
            reader = csv.DictReader(stream, delimiter='\t')
            assert reader.fieldnames == ['clustername', 'contigname'], (table, reader.fieldnames)
            rows = list(reader)
        groups = defaultdict(dict); seen = set()
        for row in rows:
            cluster, name = row['clustername'], row['contigname']
            assert cluster and name in reference and name not in seen, (category, row)
            assert name not in all_classified, ('overlapping classes', name)
            seen.add(name); groups[cluster][name] = reference[name]
        all_classified.update(seen)
        expected = {}
        for cluster, members in groups.items():
            # The fixed classifier has already split these membership tables
            # by input sample, so each final file must retain one sample.
            assert len({name.split('C', 1)[0] for name in members}) == 1, ('mixed-sample bin', cluster)
            if sum(map(len, members.values())) >= minimum:
                expected[cluster + '.fna'] = members
        files = {p.name: p for p in (products / category).glob('*.fna')}
        assert set(files) == set(expected), (category, 'missing/foreign final bins', set(files) ^ set(expected))
        for name, path in files.items():
            assert fasta(path) == expected[name], ('incorrect original DNA/members', category, name)
            hashes[category + '/' + name] = hashlib.sha256(path.read_bytes()).hexdigest()
        counts[category] = dict(memberships=len(rows), clusters=len(groups), written_bins=len(files),
                                written_memberships=sum(map(len, expected.values())), minimum_total_length=minimum)
        hashes[table.name] = hashlib.sha256(table.read_bytes()).hexdigest()
    for name in ['plasmid_scores.tsv', 'virus_genomes_scores.tsv']:
        path = products / name
        with path.open() as stream:
            reader = csv.DictReader(stream, delimiter='\t')
            assert reader.fieldnames == ['clustername', 'chromosome_score', 'plasmid_score', 'virus_score'], (name, reader.fieldnames)
            rows = list(reader)
        for row in rows:
            values = [float(row[key]) for key in ['chromosome_score', 'plasmid_score', 'virus_score']]
            assert row['clustername'] and all(math.isfinite(v) and 0 <= v <= 1 for v in values)
            assert abs(sum(values) - 1) <= 0.0021, row
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return dict(pass_=True, samples=sample_map, products=counts, product_sha256=hashes,
                scope='Final membership/schema/score-domain/FASTA and original per-sample assembly DNA, native writer length filters; not independent biological accuracy')


def check_sample_exports(products, exported):
    products, exported = Path(products), Path(exported)
    samples = json.loads((exported / 'samples.json').read_text())['samples']
    mapping = {s['tool_contig_prefix']: s for s in samples}
    assert len(mapping) == len(samples) and len({s['meta']['id'] for s in samples}) == len(samples)
    expected = {prefix: {} for prefix in mapping}
    for native in (products / 'candidate_plasmids').glob('*.fna'):
        records = fasta(native)
        prefixes = {name.split('C', 1)[0] + 'C' for name in records}
        assert len(prefixes) == 1
        prefix = next(iter(prefixes)); assert prefix in mapping
        expected[prefix][native.name] = {name[len(prefix):]: dna for name, dna in records.items()}
    counts = {}
    for prefix, sample in mapping.items():
        directory = (exported / sample['relative_directory']).resolve()
        assert directory.is_relative_to(exported.resolve())
        files = {p.name: p for p in directory.glob('*.fna')}
        assert set(files) == set(expected[prefix]), ('exported sample bins missing/foreign', prefix)
        for name, path in files.items():
            assert fasta(path) == expected[prefix][name], ('exported original contig ID/DNA differs', prefix, name)
        assert sample['bins'] == len(files)
        assert sample['state'] == ('candidate_plasmid_bins' if files else 'no_candidate_plasmid_bins')
        counts[sample['meta']['id']] = dict(bins=len(files), tool_contig_prefix=prefix, meta=sample['meta'])
    return counts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ['manifest', 'products', 'output']:
        parser.add_argument('--' + flag, type=Path, required=True)
    parser.add_argument('--sample-export', type=Path, help='Also independently check restored per-sample IDs/DNA against the native result bins')
    args = parser.parse_args()
    record = check(args.manifest, args.products); record['pass'] = record.pop('pass_')
    if args.sample_export is not None:
        record['sample_exports'] = check_sample_exports(args.products, args.sample_export)
    args.output.write_text(json.dumps(record, indent=2) + '\n')
