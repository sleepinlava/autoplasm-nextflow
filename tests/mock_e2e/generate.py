#!/usr/bin/env python3
"""Generate deterministic, valid synthetic reads; no downloaded sequences required."""
import argparse
import csv
import gzip
import json
import random
from pathlib import Path

SAMPLES = ['A__1.v1', 'A.2', 'A-3', 'B__1.v1', 'B.2', 'B-3']


def generate(destination):
    root = Path(destination).resolve()
    root.mkdir(parents=True, exist_ok=True)
    rng = random.Random(20261016)
    sequences = {name: ''.join(rng.choices('ACGT', k=size))
                 for name, size in [('plasmid_1', 4000), ('chromosome_1', 12000)]}
    fasta = ''.join(f'>{name}\n{seq}\n' for name, seq in sequences.items())
    (root / 'reference.fasta').write_text(fasta)
    rows = []
    for index, sid in enumerate(SAMPLES):
        sample = root / sid
        sample.mkdir(exist_ok=True)
        (sample / 'assembly.fasta').write_text(fasta)
        reads = [[], []]
        long_reads = []
        # Two groups with three replicates; plasmid abundance differs between groups.
        for name, seq in sequences.items():
            depth = (10 + index * 2) if name == 'plasmid_1' else (30 - index)
            for n in range(len(seq) * depth // 300):
                pos = rng.randrange(len(seq) - 350)
                fragment = seq[pos:pos + 350]
                pair = [fragment[:150], fragment[-150:].translate(str.maketrans('ACGT', 'TGCA'))[::-1]]
                for mate, read in enumerate(pair):
                    reads[mate].append(f'@{sid}_{name}_{n}/{mate+1}\n{read}\n+\n' + 'I' * len(read) + '\n')
            for n in range(20):
                pos = rng.randrange(len(seq) - 2000)
                read = seq[pos:pos + 2000]
                long_reads.append(f'@{sid}_{name}_long{n}\n{read}\n+\n' + 'I' * len(read) + '\n')
        for mate in range(2):
            with gzip.GzipFile(filename=str(sample / f'R{mate+1}.fastq.gz'), mode='wb', mtime=0) as fh:
                fh.write(''.join(reads[mate]).encode())
        with gzip.GzipFile(filename=str(sample / 'long.fastq.gz'), mode='wb', mtime=0) as fh:
            fh.write(''.join(long_reads).encode())
        rows.append([sid, 'A' if index < 3 else 'B', str(sample / 'R1.fastq.gz'),
                     str(sample / 'R2.fastq.gz'), str(sample / 'long.fastq.gz'), str(sample / 'assembly.fasta')])
    with (root / 'samples.tsv').open('w') as fh:
        writer = csv.writer(fh, delimiter='\t', lineterminator='\n')
        writer.writerow(['sample_id', 'group', 'read1', 'read2', 'long_reads', 'assembly'])
        writer.writerows(rows)
    (root / 'truth.json').write_text(json.dumps({'seed': 20261016, 'samples': SAMPLES,
        'synthetic_sequences': True, 'plasmid': 'plasmid_1', 'chromosome': 'chromosome_1',
        'note': 'Random DNA is not expected to be classified as a plasmid by real geNomad.'}, indent=2) + '\n')
    return root


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir', required=True)
    print(generate(parser.parse_args().outdir))
