#!/usr/bin/env python3
"""Generate deterministic, valid synthetic reads; no downloaded sequences required."""
import argparse
import csv
import gzip
import json
import random
from pathlib import Path

SAMPLES = ['A__1.v1', 'A.2', 'A-3', 'B__1.v1', 'B.2', 'B-3']


def generate(destination, host_removal=False):
    root = Path(destination).resolve()
    root.mkdir(parents=True, exist_ok=True)
    rng = random.Random(20261016)
    rows = []
    retained_long_reads = {}
    reference_sequences = {}
    read_origins = {}
    expected_primary_reads = {}
    host_reference_contigs = {}
    for index, sid in enumerate(SAMPLES):
        # Local IDs deliberately overlap; full DNA differs between samples.
        # A swapped reference can no longer preserve an apparent expected hit.
        sequences = {name: ''.join(rng.choices('ACGT', k=size))
                     for name, size in [('plasmid_1', 4000), ('chromosome_1', 12000)]}
        reference_sequences[sid] = sequences
        fasta = ''.join(f'>{name}\n{seq}\n' for name, seq in sequences.items())
        sample = root / sid
        sample.mkdir(exist_ok=True)
        (sample / 'assembly.fasta').write_text(fasta)
        reads = [[], []]
        long_reads = []
        host_name = ['chromosome_1', 'plasmid_1'][index] if host_removal and index < 2 else None
        host_reference_contigs[sid] = host_name
        expected_primary_reads[sid] = {kind: {name: {'count': 0, 'bases': 0} for name in sequences}
                                       for kind in ['short', 'long']}
        # Two groups with three replicates; plasmid abundance differs between groups.
        for name, seq in sequences.items():
            depth = (10 + index * 2) if name == 'plasmid_1' else (30 - index)
            for n in range(len(seq) * depth // 300):
                pos = rng.randrange(len(seq) - 350)
                fragment = seq[pos:pos + 350]
                pair = [fragment[:150], fragment[-150:].translate(str.maketrans('ACGT', 'TGCA'))[::-1]]
                for mate, read in enumerate(pair):
                    rid = f'{sid}_{name}_{n}/{mate+1}'
                    reads[mate].append(f'@{rid}\n{read}\n+\n' + 'I' * len(read) + '\n')
                    read_origins[rid] = {'sample_id': sid, 'kind': 'short', 'contig': name, 'length': len(read),
                                         'start': pos if mate == 0 else pos + 200, 'strand': '+' if mate == 0 else '-'}
                    expected_primary_reads[sid]['short'][name]['count'] += 1
                    expected_primary_reads[sid]['short'][name]['bases'] += len(read)
            for n in range(20):
                pos = rng.randrange(len(seq) - 2000)
                read = seq[pos:pos + 2000]
                rid = f'{sid}_{name}_long{n}'
                long_reads.append(f'@{rid}\n{read}\n+\n' + 'I' * len(read) + '\n')
                read_origins[rid] = {'sample_id': sid, 'kind': 'long', 'contig': name, 'length': len(read), 'start': pos, 'strand': '+'}
                if host_name != name:
                    expected_primary_reads[sid]['long'][name]['count'] += 1
                    expected_primary_reads[sid]['long'][name]['bases'] += len(read)
        for mate in range(2):
            with gzip.GzipFile(filename=str(sample / f'R{mate+1}.fastq.gz'), mode='wb', mtime=0) as fh:
                fh.write(''.join(reads[mate]).encode())
        with gzip.GzipFile(filename=str(sample / 'long.fastq.gz'), mode='wb', mtime=0) as fh:
            fh.write(''.join(long_reads).encode())
        host_reference = ''
        if host_name:
            path = sample / 'host_reference.fasta'
            path.write_text('>' + host_name + '\n' + sequences[host_name] + '\n')
            host_reference = str(path)
        retained_long_reads[sid] = [read.splitlines()[0][1:] for read in long_reads
                                   if host_name is None or not read.startswith('@' + sid + '_' + host_name + '_long')]
        rows.append([sid, 'A' if index < 3 else 'B', str(sample / 'R1.fastq.gz'),
                     str(sample / 'R2.fastq.gz'), str(sample / 'long.fastq.gz'), str(sample / 'assembly.fasta'), host_reference])
    (root / 'reference.fasta').write_text(''.join(f'>{sid}|{name}\n{dna}\n'
        for sid, sequences in reference_sequences.items() for name, dna in sequences.items()))
    with (root / 'samples.tsv').open('w') as fh:
        writer = csv.writer(fh, delimiter='\t', lineterminator='\n')
        writer.writerow(['sample_id', 'group', 'read1', 'read2', 'long_reads', 'assembly', 'host_reference'])
        writer.writerows(rows)
    (root / 'truth.json').write_text(json.dumps({'seed': 20261016, 'samples': SAMPLES,
        'synthetic_sequences': True, 'plasmid': 'plasmid_1', 'chromosome': 'chromosome_1',
        'long_read_expected_after_host_removal': retained_long_reads,
        'reference_sequences': reference_sequences, 'read_origins': read_origins,
        'expected_primary_reads': expected_primary_reads,
        'host_reference_contigs': host_reference_contigs,
        'host_removal': host_removal,
        'note': 'Random DNA is not expected to be classified as a plasmid by real geNomad.'}, indent=2) + '\n')
    return root


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir', required=True)
    print(generate(parser.parse_args().outdir))
