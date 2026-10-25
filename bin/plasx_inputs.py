#!/usr/bin/env python3
"""Keep PlasX's per-sample anvi'o genes, annotations, and source contigs aligned."""
import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3


def table(path, required):
    with Path(path).open(newline='') as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)) or not set(required) <= set(reader.fieldnames):
            raise ValueError('Missing or duplicate columns in ' + str(path))
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError('Malformed table row in ' + str(path))
    return rows


def write_table(path, columns, rows):
    with Path(path).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def fasta(path):
    path = Path(path)
    opener = gzip.open if path.suffix.lower() == '.gz' else open
    records = {}
    current = None
    with opener(path, 'rt') as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            if line.startswith('>'):
                fields = line[1:].split()
                if not fields or fields[0] in records:
                    raise ValueError('Empty or duplicate FASTA identifier')
                current = fields[0]
                records[current] = []
            else:
                if current is None or not re.fullmatch('[ACGTRYSWKMBDHVNacgtryswkmbdhvn]+', line):
                    raise ValueError('Invalid nucleotide FASTA')
                records[current].append(line.upper())
    records = {key: ''.join(parts) for key, parts in records.items()}
    if not records or any(not sequence for sequence in records.values()):
        raise ValueError('Empty FASTA or contig')
    return records


def prepare(assembly, sample, prefix):
    if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]*', sample):
        raise ValueError('Unsafe sample identifier')
    source = fasta(assembly)
    namespace = hashlib.sha256(sample.encode()).hexdigest()
    mapping = []
    with Path(str(prefix) + '.contigs.fasta').open('w') as out:
        for index, (original, sequence) in enumerate(source.items(), 1):
            internal = 'px_' + namespace + '_' + str(index)
            out.write('>' + internal + '\n' + sequence + '\n')
            mapping.append(dict(sample_id=sample, contig=internal, original_contig=original,
                                length=len(sequence), sequence_sha256=hashlib.sha256(sequence.encode()).hexdigest()))
    write_table(str(prefix) + '.id_map.tsv', ['sample_id', 'contig', 'original_contig', 'length', 'sequence_sha256'], mapping)
    return {'sample_id': sample, 'contigs': len(source), 'assembly_sha256': hashlib.sha256(Path(assembly).read_bytes()).hexdigest()}


def check_resources(cog_db=None, pfam_db=None, profiles=None, model=None):
    result = {}
    if cog_db:
        cog = Path(cog_db) / 'COG14'
        if (cog / '.VERSION').read_text().strip() != '2':
            raise ValueError('Expected anvi\'o COG14 data format 2')
        for name in ['COG.txt', 'CATEGORIES.txt', 'PID-TO-CID.cPickle', 'MISSING_COG_IDs.cPickle', 'DB_DIAMOND/COG.dmnd']:
            if not (cog / name).is_file() or not (cog / name).stat().st_size:
                raise ValueError('Missing COG14 reference file: ' + name)
        result['cog_version'] = 'COG14'
    if pfam_db:
        pfam = Path(pfam_db)
        if (pfam / 'Pfam.version').read_text().splitlines()[0].split(':')[-1].strip() != '32.0':
            raise ValueError('Expected Pfam32.0, the version used by PlasX')
        for name in ['Pfam-A.hmm', 'Pfam-A.clans.tsv', 'Pfam-A.hmm.h3f', 'Pfam-A.hmm.h3i', 'Pfam-A.hmm.h3m', 'Pfam-A.hmm.h3p']:
            if not (pfam / name).is_file() or not (pfam / name).stat().st_size:
                raise ValueError('Missing Pfam32 reference file: ' + name)
        result['pfam_version'] = '32.0'
    if profiles:
        profiles = Path(profiles)
        for identity in [90, 80, 70, 60, 50, 40, 30, 25, 20, 5]:
            for suffix in ['', '.dbtype', '.index', '_h', '_h.index']:
                path = profiles / ('clu' + str(identity) + '.profile' + suffix)
                if not path.is_file() or not path.stat().st_size:
                    raise ValueError('Missing de novo family profile: ' + path.name)
        for name in ['rep_lengths.pkl.blp', 'rep_min_align_identity.pkl.blp']:
            if not (profiles / name).is_file() or not (profiles / name).stat().st_size:
                raise ValueError('Missing de novo profile metadata: ' + name)
        result['de_novo_identities'] = [90, 80, 70, 60, 50, 40, 30, 25, 20, 5]
    if model:
        features = set()
        families = set()
        with Path(model).open(newline='') as stream:
            reader = csv.DictReader(stream, delimiter='\t')
            if not {'accession', 'PlasX_coefficient'} <= set(reader.fieldnames or []):
                raise ValueError('Expected PlasX coefficient table')
            for row in reader:
                accession = row['accession']
                if not accession or accession in features or not math.isfinite(float(row['PlasX_coefficient'])):
                    raise ValueError('Invalid or duplicate model feature/coefficient')
                features.add(accession)
                for prefix in ['COG', 'PF', 'mmseqs_']:
                    if accession.startswith(prefix):
                        families.add(prefix)
        if 'INTERCEPT' not in features or families != {'COG', 'PF', 'mmseqs_'}:
            raise ValueError('Model lacks intercept or one of the three annotation families')
        result.update(model_sha256=hashlib.sha256(Path(model).read_bytes()).hexdigest(), model_features=len(features) - 1)
    return result


def load_mapping(mapping, sequence_path, sample):
    rows = table(mapping, ['sample_id', 'contig', 'original_contig', 'length', 'sequence_sha256'])
    sequences = fasta(sequence_path)
    if not rows or len({r['contig'] for r in rows}) != len(rows) or len({r['original_contig'] for r in rows}) != len(rows):
        raise ValueError('Empty or duplicate contig mapping')
    if {r['contig'] for r in rows} != set(sequences) or {r['sample_id'] for r in rows} != {sample}:
        raise ValueError('Contig mapping does not belong to this sample FASTA')
    for row in rows:
        sequence = sequences[row['contig']]
        if int(row['length']) != len(sequence) or row['sequence_sha256'] != hashlib.sha256(sequence.encode()).hexdigest():
            raise ValueError('Contig mapping sequence mismatch')
    return {r['contig']: r for r in rows}, sequences


def load_genes(path, sequences):
    rows = table(path, ['gene_callers_id', 'contig', 'start', 'stop', 'direction', 'source', 'version', 'aa_sequence'])
    genes = {}
    for row in rows:
        key = row['gene_callers_id']
        if not re.fullmatch('[0-9]+', key) or key in genes or row['contig'] not in sequences:
            raise ValueError('Duplicate, invalid, or foreign gene identity')
        start, stop = int(row['start']), int(row['stop'])
        if not 0 <= start < stop <= len(sequences[row['contig']]) or row['direction'] not in ['f', 'r']:
            raise ValueError('Invalid gene coordinates')
        if row['source'] != 'prodigal' or row['version'] != 'v2.6.3' or not re.fullmatch('[A-Z*]+', row['aa_sequence']):
            raise ValueError('Unexpected gene caller or empty protein sequence')
        genes[key] = row
    return genes


def check_annotations(path, genes, de_novo=False):
    required = ['gene_callers_id', 'accession', 'e_value'] + (['contig', 'start', 'stop', 'direction'] if de_novo else ['source'])
    rows = table(path, required)
    for row in rows:
        if row['gene_callers_id'] not in genes:
            raise ValueError('Annotation references an unknown gene')
        gene = genes[row['gene_callers_id']]
        value = float(row['e_value'])
        if not math.isfinite(value) or value < 0:
            raise ValueError('Invalid annotation e-value')
        if de_novo:
            if any(row[key] != gene[key] for key in ['contig', 'start', 'stop', 'direction']):
                raise ValueError('De novo annotation belongs to another gene/contig')
            valid = re.fullmatch('mmseqs_(90|80|70|60|50|40|30|25|20|5)_[0-9]+', row['accession'])
        else:
            pattern = {'COG14_FUNCTION': 'COG[0-9]{4}', 'Pfam': 'PF[0-9]{5}\\.[0-9]+'}
            valid = row['source'] in pattern and all(re.fullmatch(pattern[row['source']], accession) for accession in row['accession'].split('!!!'))
        if not valid:
            raise ValueError('Unexpected annotation source or accession')
    return rows


def validate_anvio(database, genes, sequences, annotations=None):
    with sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True) as connection:
        metadata = dict(connection.execute('SELECT key, value FROM self'))
        if metadata.get('version') != '20' or metadata.get('db_type') != 'contigs':
            raise ValueError('Unexpected anvi\'o database format')
        if not {'COG14_FUNCTION', 'Pfam'} <= set((metadata.get('gene_function_sources') or '').split(',')):
            raise ValueError('anvi\'o database lacks a completed COG14/Pfam annotation source')
        stored = dict(connection.execute('SELECT contig, sequence FROM contig_sequences'))
        if stored != sequences:
            raise ValueError('anvi\'o database sequences differ from source FASTA')
        fields = ['gene_callers_id', 'contig', 'start', 'stop', 'direction', 'source', 'version']
        native = connection.execute('SELECT ' + ','.join(fields) + ' FROM genes_in_contigs').fetchall()
        exported = {tuple(row[field] for field in fields) for row in genes.values()}
        if len(native) != len(genes) or {tuple(str(value) for value in row) for row in native} != exported:
            raise ValueError('Exported gene calls differ from sample database')
        proteins = {str(key): value for key, value in connection.execute('SELECT gene_callers_id, sequence FROM gene_amino_acid_sequences')}
        if proteins != {key: row['aa_sequence'] for key, row in genes.items()}:
            raise ValueError('Exported amino acid sequences differ from sample database')
        if annotations is not None:
            exported = table(annotations, ['gene_callers_id', 'source', 'accession', 'function', 'e_value'])
            native = connection.execute("SELECT gene_callers_id, source, accession, function, e_value FROM gene_functions WHERE source IN ('COG14_FUNCTION','Pfam')").fetchall()
            expected = sorted((str(gene), source, accession, function, float(evalue)) for gene, source, accession, function, evalue in native)
            observed = sorted((row['gene_callers_id'], row['source'], row['accession'], row['function'], float(row['e_value'])) for row in exported)
            if observed != expected:
                raise ValueError('Exported annotations differ from this sample database')


def finalize(scores, mapping, sequences, genes, cogs, denovo, output, state, sample):
    cogs = check_annotations(cogs, genes)
    denovo = check_annotations(denovo, genes, de_novo=True)
    annotated = {genes[row['gene_callers_id']]['contig'] for row in cogs + denovo}
    predictions = table(scores, ['contig', 'score'])
    seen = set()
    for row in predictions:
        key = row['contig']
        value = float(row['score'])
        if key in seen or key not in mapping or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError('Invalid, duplicate, or foreign PlasX score')
        seen.add(key)
    if seen != annotated:
        raise ValueError('PlasX score domain differs from annotated contigs')
    # Preserve original floating point text. Missing annotations are unassessed,
    # never an invented zero probability or intercept-only prediction.
    write_table(output, ['contig', 'score'], [{'contig': mapping[row['contig']]['original_contig'], 'score': row['score']} for row in predictions])
    gene_contigs = {row['contig'] for row in genes.values()}
    statuses = []
    for key, row in mapping.items():
        status = 'scored' if key in seen else ('not_assessed_no_annotations' if key in gene_contigs else 'not_assessed_no_genes')
        statuses.append({'sample_id': sample, 'contig': row['original_contig'], 'status': status})
    write_table(state, ['sample_id', 'contig', 'status'], statuses)
    return {'sample_id': sample, 'genes': len(genes), 'cog_pfam_annotations': len(cogs), 'de_novo_annotations': len(denovo),
            'scored_contigs': len(seen), 'unassessed_contigs': len(mapping) - len(seen)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['prepare', 'resources', 'check-anvio', 'finalize'])
    for argument in ['assembly', 'sample', 'prefix', 'mapping', 'fasta', 'genes', 'annotations', 'database', 'de-novo', 'scores', 'output', 'state', 'record', 'cog-db', 'pfam-db', 'profiles', 'model']:
        parser.add_argument('--' + argument)
    args = parser.parse_args()
    if args.operation == 'resources':
        result = check_resources(args.cog_db, args.pfam_db, args.profiles, args.model)
    elif args.operation == 'prepare':
        result = prepare(args.assembly, args.sample, args.prefix)
    else:
        mapping, sequences = load_mapping(args.mapping, args.fasta, args.sample)
        genes = load_genes(args.genes, sequences)
        if args.operation == 'check-anvio':
            validate_anvio(args.database, genes, sequences, args.annotations)
            annotations = check_annotations(args.annotations, genes)
            result = {'sample_id': args.sample, 'genes': len(genes), 'annotations': len(annotations)}
        else:
            result = finalize(args.scores, mapping, sequences, genes, args.annotations, args.de_novo, args.output, args.state, args.sample)
    if args.record:
        Path(args.record).write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
