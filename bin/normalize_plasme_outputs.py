#!/usr/bin/env python3
"""Validate PLASMe v1.1's exact FASTA/report pair and export positive calls.

The report is a positive-only set, including BLASTn hits with score=nan.
Keep source_score as evidence; do not re-threshold Transformer probabilities.
"""
import argparse
import csv
from pathlib import Path
import sys

REPORT_COLUMNS = ['contig', 'length', 'reference', 'order', 'evidence', 'score', 'amb_region']


def fasta(path):
    records = {}
    name = None
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if line.startswith('>'):
            words = line[1:].split()
            if not words or words[0] in records:
                raise ValueError('Empty or duplicate FASTA ID at {}:{}'.format(path, number))
            name = words[0]
            records[name] = ''
        elif line.strip():
            if name is None:
                raise ValueError('Sequence before FASTA header in {}'.format(path))
            records[name] += ''.join(line.split())
    if any(not sequence for sequence in records.values()):
        raise ValueError('Empty FASTA sequence in {}'.format(path))
    return records


def normalize(assembly, plasmids, report, output):
    for path in [assembly, plasmids, report]:
        if not path.is_file():
            raise ValueError('Missing PLASMe output/input contract file: {}'.format(path))
    source = fasta(assembly)
    positive = fasta(plasmids)
    with report.open(newline='') as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        if reader.fieldnames != REPORT_COLUMNS:
            raise ValueError('Invalid PLASMe report header: {}'.format(report))
        rows = list(reader)
    seen = set()
    for number, row in enumerate(rows, 2):
        cid = row['contig']
        if None in row or any(v is None for v in row.values()) or not cid or cid != cid.strip():
            raise ValueError('Invalid PLASMe report row at {}:{}'.format(report, number))
        if cid in seen:
            raise ValueError('Duplicate PLASMe report ID {} at {}:{}'.format(cid, report, number))
        seen.add(cid)
        if cid not in source or cid not in positive:
            raise ValueError('Unresolved PLASMe report ID {} at {}:{}'.format(cid, report, number))
        if row['length'] != str(len(source[cid])) or positive[cid] != source[cid]:
            raise ValueError('PLASMe sequence/length mismatch for {} at {}:{}'.format(cid, report, number))
    if seen != set(positive):
        raise ValueError('PLASMe report/FASTA IDs differ: {}'.format(report))
    # Validate the complete pair before creating the consumer-facing table.
    with output.open('w', newline='') as stream:
        fields = ['contig_id', 'classification', 'source_score', 'evidence', 'reference', 'order', 'amb_region']
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter='\t', lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({'contig_id': row['contig'], 'classification': 'plasmid',
                             'source_score': row['score'], 'evidence': row['evidence'],
                             'reference': row['reference'], 'order': row['order'], 'amb_region': row['amb_region']})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ['assembly', 'plasmids', 'report', 'output']:
        parser.add_argument('--' + flag, type=Path, required=True)
    args = parser.parse_args()
    try:
        normalize(args.assembly, args.plasmids, args.report, args.output)
    except (ValueError, OSError, UnicodeError, csv.Error) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
