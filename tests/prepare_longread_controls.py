#!/usr/bin/env python3
"""Build an explicit synthetic split-read control from fixed upstream DNA.

Two named technical records contain a known 4kb+4kb junction. They are not
biological replicates, naturally occurring plasmids or host-linking truth.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assembly', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = {}
    with args.assembly.open() as stream:
        for line in stream:
            if line.startswith('>'):
                key = line[1:].split()[0]
                assert key not in source
                source[key] = ''
            elif line.strip():
                source[key] += line.strip()
    selected = [(key, dna) for key, dna in source.items() if len(dna) >= 10000][:6]
    assert len(selected) == 6
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'test_data').mkdir()
    (args.output / 'minigut.fasta').write_text(''.join('>' + key + '\n' + dna + '\n' for key, dna in selected))
    sequence = selected[0][1][:4000] + selected[5][1][:4000]
    with gzip.open(args.output / 'test_data/minigut_reads.fastq.gz', 'wt') as stream:
        for index in [1, 2]:
            stream.write(f'@controlled_bridge_{index}\n{sequence}\n+\n' + 'I' * len(sequence) + '\n')
    manifest = {'kind': 'synthetic_spanning_read_execution_control', 'plasmid_id': selected[0][0],
                'host_id': selected[5][0], 'expected_supporting_reads': 2,
                'source_sha256': hashlib.sha256(args.assembly.read_bytes()).hexdigest(),
                'selected_contig_ids': [key for key, _ in selected], 'junction': 'first4000bp of first contig + first4000bp of sixth contig',
                'scope': 'Controlled mapper/BAM/R counter positive only; no biological replicate, plasmid or host truth'}
    (args.output / 'control.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
