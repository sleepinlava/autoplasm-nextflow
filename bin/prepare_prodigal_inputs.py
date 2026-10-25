#!/usr/bin/env python3
"""Keep Prodigal proteins linked to their source contigs and gene coordinates.

No gene calling, translation, circularity inference or model thresholds occur
here. Inputs must be the GFF/AA/CDS outputs of the same Prodigal invocation.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import re


def text(path):
    data = Path(path).read_bytes()
    if data[:2] == b'\x1f\x8b':
        data = gzip.decompress(data)
    return data.decode('utf-8')


def fasta(path, alphabet, allow_empty=False):
    records = {}
    header = None
    sequence = []

    def append():
        if header is None:
            return
        identifier = header.split()[0]
        value = ''.join(sequence)
        if identifier in records or not value or re.search(alphabet, value):
            raise ValueError('Duplicate ID, empty or invalid sequence: ' + identifier)
        records[identifier] = (header, value)

    for line in text(path).splitlines():
        if not line.strip():
            continue
        if line.startswith('>'):
            append()
            header = line[1:].strip()
            if not header:
                raise ValueError('Empty FASTA identifier')
            sequence = []
        else:
            if header is None:
                raise ValueError('Sequence before FASTA header')
            sequence.append(line.strip())
    append()
    if not records and not allow_empty:
        raise ValueError('Empty FASTA input')
    return records


def attributes(value):
    fields = [part.split('=', 1) for part in value.strip(';').split(';') if part]
    if any(len(part) != 2 for part in fields) or len({p[0] for p in fields}) != len(fields):
        raise ValueError('Malformed or duplicate Prodigal attributes')
    return dict(fields)


def prepare(genome, gff, proteins, cds, output):
    dna = fasta(genome, '[^ACGTRYSWKMBDHVNacgtryswkmbdhvn]')
    aa = fasta(proteins, '[^A-Z*]', allow_empty=True)
    nt = fasta(cds, '[^ACGTRYSWKMBDHVNacgtryswkmbdhvn]', allow_empty=True)
    if aa.keys() != nt.keys():
        raise ValueError('Protein/CDS identifiers differ')
    topology = {}
    for identifier, (header, _) in dna.items():
        tokens = set(header.split()[1:])
        circular = bool(tokens & {'topology=circular', 'circular=true'})
        linear = bool(tokens & {'topology=linear', 'circular=false', 'not_circular'})
        if circular and linear:
            raise ValueError('Conflicting topology markers: ' + identifier)
        if circular and (':' in identifier or identifier.startswith('#')):
            raise ValueError('Circular contig ID cannot be represented in a MacSyFinder topology file: ' + identifier)
        topology[identifier] = ('circular' if circular else 'linear',
                                'explicit_header' if circular or linear else 'unknown_treated_as_linear')
    # Prodigal's GFF ID is seqnum_gene; its protein ID is contigID_gene.
    rows = []
    seen = set()
    sequence_metadata = {}
    current = None
    table = None
    for line in text(gff).splitlines():
        if line.startswith('# Sequence Data: '):
            match = re.fullmatch(r'# Sequence Data: seqnum=(\d+);seqlen=(\d+);seqhdr="(.*)"', line)
            if not match:
                raise ValueError('Malformed Prodigal sequence metadata')
            number, length, header = match.groups()
            current = header.split()[0]
            if current not in dna or current in sequence_metadata or len(dna[current][1]) != int(length):
                raise ValueError('GFF/source sequence metadata mismatch: ' + current)
            sequence_metadata[current] = number
            table = None
        elif line.startswith('# Model Data: '):
            match = re.search(r'(?:^|;)transl_table=(\d+);', line)
            if current is None or not match or 'version=Prodigal.v2.6.3;' not in line:
                raise ValueError('Expected Prodigal 2.6.3 model metadata')
            table = int(match.group(1))
        elif not line or line.startswith('#'):
            continue
        else:
            cols = line.split('\t')
            if len(cols) != 9 or cols[0] != current or cols[1:3] != ['Prodigal_v2.6.3', 'CDS'] or cols[7] != '0' or table is None:
                raise ValueError('Invalid Prodigal CDS GFF record')
            attr = attributes(cols[8])
            match = re.fullmatch(re.escape(sequence_metadata[current]) + r'_(\d+)', attr.get('ID', ''))
            if not match:
                raise ValueError('GFF gene identifier does not match its replicon')
            pid = current + '_' + match.group(1)
            start, end = int(cols[3]), int(cols[4])
            strand = cols[6]
            if pid in seen or pid not in aa or not (1 <= start <= end <= len(dna[current][1])) or strand not in ('+', '-'):
                raise ValueError('Missing, duplicate or invalid Prodigal gene: ' + pid)
            for header, _ in (aa[pid], nt[pid]):
                parts = header.split(' # ')
                if len(parts) != 5 or parts[:4] != [pid, str(start), str(end), '1' if strand == '+' else '-1']:
                    raise ValueError('Protein/CDS coordinate header mismatch: ' + pid)
                h_attr = attributes(parts[4])
                if any(h_attr.get(k) != attr.get(k) for k in ('ID', 'partial', 'start_type')):
                    raise ValueError('Protein/CDS gene attributes mismatch: ' + pid)
            segment = dna[current][1][start - 1:end].upper()
            if strand == '-':
                segment = segment.translate(str.maketrans('ACGTRYSWKMBDHVN', 'TGCAYRSWMKVHDBN'))[::-1]
            if nt[pid][1].upper() != segment or len(segment) % 3 or len(aa[pid][1]) != len(segment) // 3:
                raise ValueError('CDS/source DNA or protein length mismatch: ' + pid)
            if '*' in aa[pid][1][:-1]:
                raise ValueError('Internal protein stop: ' + pid)
            rows.append({'protein_id': pid, 'contig_id': current, 'start': start, 'end': end,
                         'strand': strand, 'translation_table': table, 'partial': attr['partial'],
                         'topology': topology[current][0], 'topology_source': topology[current][1]})
            seen.add(pid)
    if sequence_metadata.keys() != dna.keys() or seen != aa.keys():
        raise ValueError('Incomplete Prodigal GFF/FASTA record sets')
    order = {identifier: number for number, identifier in enumerate(dna)}
    rows.sort(key=lambda row: (order[row['contig_id']], row['start'], row['end'], row['protein_id']))
    # Each contig remains one contiguous gembase group; the final underscore
    # separates the contig ID and gene number, even when contig IDs contain '_'.
    payload = ''.join('>' + aa[row['protein_id']][0] + '\n' + aa[row['protein_id']][1] + '\n' for row in rows)
    manifest = {'schema': 1, 'gene_caller': 'Prodigal 2.6.3',
                'state': 'proteins_ready' if rows else 'no_predicted_proteins',
                'protein_count': len(rows), 'contig_count': len(dna),
                'source_sha256': {label: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                                  for label, path in [('genome', genome), ('gff', gff), ('proteins', proteins), ('cds', cds)]},
                'replicons': [{'contig_id': identifier, 'protein_count': sum(r['contig_id'] == identifier for r in rows),
                               'topology': topology[identifier][0], 'topology_source': topology[identifier][1]}
                              for identifier in dna]}
    table_out = io.StringIO()
    fields = ['protein_id', 'contig_id', 'start', 'end', 'strand', 'translation_table', 'partial', 'topology', 'topology_source']
    writer = csv.DictWriter(table_out, fields, delimiter='\t', lineterminator='\n')
    writer.writeheader(); writer.writerows(rows)
    outputs = {'proteins.faa': payload, 'gene_map.tsv': table_out.getvalue(),
               # MacSyLib 1.0.4 parses "replicon: topology" (not TSV).
               # All other replicons use --replicon-topology linear.
               'replicon_topology.txt': ''.join(identifier + ': circular\n' for identifier in dna
                                              if topology[identifier][0] == 'circular' and any(r['contig_id'] == identifier for r in rows)),
               'manifest.json': json.dumps(manifest, indent=2) + '\n'}
    output = Path(output)
    if output.exists():
        raise ValueError('Protein input output directory already exists')
    output.mkdir(parents=True)
    for name, data in outputs.items():
        (output/name).write_text(data)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('genome', 'gff', 'proteins', 'cds', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    prepare(**vars(args))
