#!/usr/bin/env python3
"""Prepare stable whole-cohort PlasMAAG inputs and restore sample/contig identity."""
import argparse
from collections import defaultdict
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import shutil


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fasta(path):
    path = Path(path)
    with path.open('rb') as stream:
        compressed = stream.read(2) == b'\x1f\x8b'
    records = {}; current = None
    with (gzip.open(path, 'rt') if compressed else path.open()) as stream:
        for number, line in enumerate(stream, 1):
            line = line.strip()
            if not line:
                continue
            if line.startswith('>'):
                current = line[1:].split()[0]
                if not current or current in records:
                    raise ValueError(f'Empty/duplicate contig ID: {path}:{number}')
                records[current] = ''
            else:
                if current is None or not re.fullmatch('[ACGTRYSWKMBDHVNacgtryswkmbdhvn]+', line):
                    raise ValueError(f'Invalid nucleotide FASTA: {path}:{number}')
                records[current] += line.upper()
    if not records or any(not seq for seq in records.values()):
        raise ValueError('Empty assembly sequence: ' + str(path))
    return records


def write_fasta(path, records):
    with Path(path).open('w') as stream:
        for name, sequence in records.items():
            stream.write('>' + name + '\n' + sequence + '\n')


def prepare(specification, output):
    spec = json.loads(Path(specification).read_text())
    assembler = spec['assembler']
    if assembler not in ['metaspades', 'megahit']:
        raise ValueError('PlasMAAG supports the paired-read metaspades/megahit cohort adapter only')
    rows = spec['records']
    if not rows:
        raise ValueError('PlasMAAG cohort is empty')
    ids = [row['meta']['id'] for row in rows]
    if any(not isinstance(x, str) or not x for x in ids) or len(set(ids)) != len(ids):
        raise ValueError('PlasMAAG requires unique nonempty sample IDs')
    output = Path(output).resolve()
    if re.search(r'\s', str(output)):
        raise ValueError('Fixed PlasMAAG shell rules require a work directory without whitespace')
    # Resolve everything before writing a partial cohort manifest.
    plan = []; seen_reads = set()
    for index, row in enumerate(sorted(rows, key=lambda r: r['meta']['id'])):
        pair = [Path(p).resolve() for p in row['reads']]
        if len(pair) != 2 or any(not p.is_file() or not p.stat().st_size for p in pair):
            raise ValueError('PlasMAAG requires two nonempty read files per sample')
        if any(str(p) in seen_reads for p in pair) or pair[0] == pair[1]:
            raise ValueError('PlasMAAG read file assigned more than once')
        seen_reads.update(map(str, pair))
        assembly = Path(row['assembly']).resolve()
        source = assembly / 'contigs.fasta' if assembler == 'metaspades' else assembly
        records = fasta(source)
        if assembler == 'metaspades':
            for name in ['contigs.paths', 'assembly_graph_after_simplification.gfa']:
                if not (assembly / name).is_file() or not (assembly / name).stat().st_size:
                    raise ValueError('PlasMAAG SPAdes bundle missing: ' + name)
        plan.append((index, row['meta'], pair, assembly, source, records))
    output.mkdir(parents=True, exist_ok=False)
    mapping = []; manifest_rows = []
    for index, meta, pair, assembly, source, records in plan:
        folder = output / ('sample_' + str(index)); folder.mkdir()
        reads = []
        for number, original in enumerate(pair, 1):
            with original.open('rb') as stream:
                suffix = '.fastq.gz' if stream.read(2) == b'\x1f\x8b' else '.fastq'
            link = folder / ('read' + str(number) + suffix)
            link.symlink_to(original); reads.append(str(link))
        canonical = folder / 'contigs.fasta'; write_fasta(canonical, records)
        if assembler == 'metaspades':
            for name in ['contigs.paths', 'assembly_graph_after_simplification.gfa']:
                shutil.copyfile(assembly / name, folder / name)
        manifest_rows.append(reads + [str(folder if assembler == 'metaspades' else canonical)])
        mapping.append(dict(index=index, tool_contig_prefix=f'S{index}C', meta=meta,
                            assembly=str(canonical), original_assembly=str(source), original_sha256=sha(source),
                            canonical_sha256=sha(canonical), contigs=len(records), nucleotides=sum(map(len, records.values()))))
    with (output / 'reads-and-assembly.tsv').open('w') as stream:
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        writer.writerow(['read1', 'read2', 'assembly_dir' if assembler == 'metaspades' else 'contigs'])
        writer.writerows(manifest_rows)
    state = dict(schema=1, assembler=assembler, samples=mapping,
                 scope='Full assemblies and paired reads, stable sorted sample-ID order; no filtering by upstream plasmid calls')
    (output / 'sample-map.json').write_text(json.dumps(state, indent=2) + '\n')
    return state


def table(path, fields):
    with Path(path).open() as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        if reader.fieldnames != fields:
            raise ValueError('Unexpected native PlasMAAG header: ' + str(path))
        rows = list(reader)
    if any(None in r or any(v is None for v in r.values()) for r in rows):
        raise ValueError('Malformed native PlasMAAG table: ' + str(path))
    return rows


def validate(sample_map, native_results, output):
    state = json.loads(Path(sample_map).read_text()); native_results = Path(native_results)
    reference = {}; origin = {}; original_meta = {}
    for sample in state['samples']:
        prefix = sample['tool_contig_prefix']; original_meta[prefix] = sample['meta']
        if sha(sample['assembly']) != sample['canonical_sha256']:
            raise ValueError('Prepared cohort assembly changed')
        for name, sequence in fasta(sample['assembly']).items():
            reference[prefix + name] = sequence; origin[prefix + name] = (prefix, name)
    groups_by_class = {}; observed_all = set()
    for category, minimum in [('candidate_plasmids', 1), ('candidate_genomes', 200000), ('candidate_virus', 1)]:
        rows = table(native_results / (category + '.tsv'), ['clustername', 'contigname'])
        groups = defaultdict(dict); seen = set()
        for row in rows:
            cluster, name = row['clustername'], row['contigname']
            if not re.fullmatch(r'[A-Za-z0-9_.-]+', cluster) or name not in reference or name in seen or name in observed_all:
                raise ValueError('Unknown/duplicate/mixed-class native PlasMAAG membership')
            seen.add(name); groups[cluster][name] = reference[name]
        observed_all.update(seen)
        expected = {}
        for cluster, members in groups.items():
            if len({origin[name][0] for name in members}) != 1:
                raise ValueError('Native PlasMAAG bin contains different samples')
            if sum(map(len, members.values())) >= minimum:
                expected[cluster] = members
        files = {p.stem: p for p in (native_results / category).glob('*.fna')}
        if set(files) != set(expected):
            raise ValueError('Native PlasMAAG final bin set differs from membership/length contract')
        for cluster, path in files.items():
            if fasta(path) != expected[cluster]:
                raise ValueError('Native PlasMAAG bin DNA differs from original sample')
        groups_by_class[category] = expected
    for name in ['plasmid_scores.tsv', 'virus_genomes_scores.tsv']:
        rows = table(native_results / name, ['clustername', 'chromosome_score', 'plasmid_score', 'virus_score'])
        for row in rows:
            values = [float(row[k]) for k in ['chromosome_score', 'plasmid_score', 'virus_score']]
            if not row['clustername'] or any(not math.isfinite(v) or not 0 <= v <= 1 for v in values) or abs(sum(values) - 1) > .0021:
                raise ValueError('Invalid native PlasMAAG score')
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(native_results, output / 'native_results')
    samples = []
    for prefix, meta in original_meta.items():
        key = hashlib.sha256(meta['id'].encode()).hexdigest(); folder = output / 'per_sample' / key
        folder.mkdir(parents=True); count = 0
        for cluster, members in groups_by_class['candidate_plasmids'].items():
            if {origin[name][0] for name in members} != {prefix}:
                continue
            write_fasta(folder / (cluster + '.fna'), {origin[name][1]: dna for name, dna in members.items()}); count += 1
        samples.append(dict(meta=meta, tool_contig_prefix=prefix, relative_directory=str(folder.relative_to(output)),
                            bins=count, state='candidate_plasmid_bins' if count else 'no_candidate_plasmid_bins'))
    manifest = dict(schema=1, samples=samples, native_results='native_results',
                    scope='Native candidates; per-sample plasmid bins restore original contig IDs and metadata; not closed-plasmid or biological-accuracy certification')
    (output / 'samples.json').write_text(json.dumps(manifest, indent=2) + '\n')
    shutil.copyfile(sample_map, output / 'sample-map.json')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    prepare_parser = sub.add_parser('prepare'); prepare_parser.add_argument('--spec', required=True); prepare_parser.add_argument('--output', required=True)
    checked = sub.add_parser('validate'); checked.add_argument('--sample-map', required=True); checked.add_argument('--results', required=True); checked.add_argument('--output', required=True)
    args = parser.parse_args()
    if args.command == 'prepare': prepare(args.spec, args.output)
    else: validate(args.sample_map, args.results, args.output)


if __name__ == '__main__':
    main()
