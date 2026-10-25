#!/usr/bin/env python3
"""Convert the fixed HOTSPOT taxonomy table without treating CR as a taxon."""
import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path

RANKS = ['Phylum', 'Class', 'Order', 'Family', 'Genus', 'Species']
INPUT_HEADER = ['Contig', *RANKS]
OUTPUT_HEADER = ['plasmid_id', 'host_id', 'sample_id', 'evidence_type', 'score', 'supporting_data']


def source_ids(path):
    data = Path(path).read_bytes()
    if data[:2] == b'\x1f\x8b':
        data = gzip.decompress(data)
    identifiers = []
    seen = set()
    for line in data.decode('utf-8').splitlines():
        if line.startswith('>'):
            fields = line[1:].split()
            if not fields or fields[0] in seen:
                raise ValueError('Empty or duplicate HOTSPOT source FASTA ID')
            identifiers.append(fields[0])
            seen.add(fields[0])
        elif line.strip() and not identifiers:
            raise ValueError('HOTSPOT source is not FASTA')
    if not identifiers:
        raise ValueError('Empty HOTSPOT source FASTA')
    return identifiers


def convert(lineage, sample_id, output, manifest, fasta=None):
    if not sample_id or any(c in sample_id for c in '\t\r\n'):
        raise ValueError('Invalid HOTSPOT sample ID')
    allowed = source_ids(fasta) if fasta is not None else None
    allowed_set = set(allowed) if allowed is not None else None
    seen = set()
    links = []
    no_taxon = []
    with Path(lineage).open(encoding='utf-8', newline='') as stream:
        reader = csv.reader(stream, delimiter='\t')
        if next(reader, None) != INPUT_HEADER:
            raise ValueError('Unexpected HOTSPOT lineage header/rank order')
        for row in reader:
            if len(row) != len(INPUT_HEADER) or any(any(c in value for c in '\t\r\n') for value in row):
                raise ValueError('Malformed HOTSPOT lineage row')
            identifier = row[0]
            if not identifier or identifier in seen or (allowed_set is not None and identifier not in allowed_set):
                raise ValueError('Empty, duplicate or foreign HOTSPOT contig ID: ' + identifier)
            seen.add(identifier)
            # csv.reader consumes the CRLF record ending before missing-value
            # checks. Do not reinterpret '-' as a species or confidence score.
            ranks = [value for value in row[1:] if value not in ('', '-')]
            if any(not value.strip() for value in ranks):
                raise ValueError('Whitespace-only HOTSPOT taxon')
            if not ranks:
                no_taxon.append(identifier)
                continue
            links.append([identifier, ranks[-1], sample_id, 'hotspot', '',
                          'method=hotspot;lineage=' + '>'.join(ranks)])
    table = io.StringIO()
    writer = csv.writer(table, delimiter='\t', lineterminator='\n')
    writer.writerow(OUTPUT_HEADER); writer.writerows(links)
    result = {'schema': 1, 'sample_id': sample_id, 'lineage_rows': len(seen), 'host_links': len(links),
              'lineage_sha256': hashlib.sha256(Path(lineage).read_bytes()).hexdigest(),
              'no_taxon_in_lineage': no_taxon,
              'source_ids_not_in_lineage': [identifier for identifier in allowed if identifier not in seen] if allowed is not None else None,
              'scope': 'deepest reported taxon; omitted/unscored IDs are not negative host predictions'}
    if fasta is not None:
        result['source_fasta_sha256'] = hashlib.sha256(Path(fasta).read_bytes()).hexdigest()
    output, manifest = Path(output), Path(manifest)
    if output.resolve() == manifest.resolve() or output.exists() or manifest.exists():
        raise ValueError('HOTSPOT conversion output already exists or overlaps')
    if any(p.resolve() == Path(lineage).resolve() or (fasta is not None and p.resolve() == Path(fasta).resolve()) for p in [output, manifest]):
        raise ValueError('HOTSPOT conversion cannot overwrite its input')
    output.write_text(table.getvalue())
    manifest.write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['lineage', 'sample-id', 'output', 'manifest']:
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--fasta')
    convert(**vars(parser.parse_args()))
