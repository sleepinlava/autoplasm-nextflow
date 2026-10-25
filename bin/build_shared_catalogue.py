#!/usr/bin/env python3
"""Build a sequence-specific, strand-invariant nucleotide catalogue.

Only complete sequence identity (including reverse complement) is collapsed.
This is not ANI clustering, plasmid family inference or circular rotation
normalization. SQLite keeps the full collection off the Python heap.
"""
import argparse
from contextlib import closing
import csv
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile

ALPHABET = frozenset('ACGTRYSWKMBDHVN')
COMPLEMENT = str.maketrans('ACGTRYSWKMBDHVN', 'TGCAYRSWMKVHDBN')


def records(path):
    """Empty FASTA is a valid zero-record input; empty records are invalid."""
    name, pieces, seen = None, [], set()
    with (gzip.open(path, 'rt') if path.suffix.lower() == '.gz' else path.open()) as stream:
        for line_number, raw in enumerate(stream, 1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith('>'):
                if name is not None:
                    if not pieces:
                        raise ValueError(f'{path}: empty sequence {name}')
                    yield name, ''.join(pieces)
                fields = line[1:].split()
                if not fields or fields[0] in seen:
                    raise ValueError(f'{path}:{line_number}: empty or duplicate FASTA ID')
                name, pieces = fields[0], []
                seen.add(name)
            else:
                if name is None:
                    raise ValueError(f'{path}:{line_number}: sequence before header')
                dna = line.upper()
                if set(dna) - ALPHABET:
                    raise ValueError(f'{path}:{line_number}: invalid IUPAC DNA in {name}')
                pieces.append(dna)
    if name is not None:
        if not pieces:
            raise ValueError(f'{path}: empty sequence {name}')
        yield name, ''.join(pieces)


def canonical(dna):
    reverse = dna.translate(COMPLEMENT)[::-1]
    return (dna, '+') if dna <= reverse else (reverse, '-')


def digest(dna):
    return hashlib.sha256(dna.encode('ascii')).hexdigest()


def file_digest(path):
    checksum = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(block)
    return checksum.hexdigest()


def write_tsv(path, fields, rows):
    with path.open('w') as stream:
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        writer.writerow(fields)
        writer.writerows(rows)


def build(sample_ids, assemblies, plasmids, output, expected_samples=None):
    if not sample_ids or len(sample_ids) != len(assemblies) or len(sample_ids) != len(plasmids):
        raise ValueError('sample IDs, assemblies and plasmids must have the same nonzero length')
    if len(set(sample_ids)) != len(sample_ids) or any(not sid or any(c in sid for c in '\t\r\n') for sid in sample_ids):
        raise ValueError('sample IDs must be nonempty, unique TSV values')
    if expected_samples is not None and len(sample_ids) != expected_samples:
        raise ValueError('shared catalogue: missing/unexpected assembly sample')
    if output.exists():
        raise ValueError(f'refusing to overwrite catalogue: {output}')
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.' + output.name + '-', dir=output.parent))
    try:
        with closing(sqlite3.connect(stage / 'working.sqlite')) as db:
            db.executescript('''
                CREATE TABLE refs (feature_id TEXT PRIMARY KEY, dna TEXT NOT NULL, length_bp INTEGER NOT NULL);
                CREATE TABLE sources (sample_id TEXT, contig_id TEXT, feature_id TEXT, orientation TEXT,
                                      is_plasmid INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(sample_id, contig_id));
                CREATE INDEX source_feature ON sources(feature_id);
            ''')
            sample_rows, input_files = [], []
            for sid, assembly, candidate in sorted(zip(sample_ids, assemblies, plasmids)):
                input_files.append({'sample_id': sid, 'assembly_sha256': file_digest(assembly),
                                    'plasmids_sha256': file_digest(candidate)})
                n_assembly = n_plasmid = 0
                for cid, dna in records(assembly):
                    seq, orientation = canonical(dna)
                    fid = 'seq_' + digest(seq)
                    existing = db.execute('SELECT dna FROM refs WHERE feature_id=?', (fid,)).fetchone()
                    if existing is not None and existing[0] != seq:
                        raise ValueError('sequence hash collision')
                    db.execute('INSERT OR IGNORE INTO refs VALUES (?, ?, ?)', (fid, seq, len(seq)))
                    db.execute('INSERT INTO sources(sample_id, contig_id, feature_id, orientation) VALUES (?, ?, ?, ?)', (sid, cid, fid, orientation))
                    n_assembly += 1
                for cid, dna in records(candidate):
                    source = db.execute('SELECT feature_id FROM sources WHERE sample_id=? AND contig_id=?', (sid, cid)).fetchone()
                    if source is None:
                        raise ValueError(f'{sid}: candidate {cid} is absent from its assembly')
                    seq, _ = canonical(dna)
                    if source[0] != 'seq_' + digest(seq):
                        raise ValueError(f'{sid}: candidate {cid} sequence differs from its assembly')
                    db.execute('UPDATE sources SET is_plasmid=1 WHERE sample_id=? AND contig_id=?', (sid, cid))
                    n_plasmid += 1
                sample_rows.append([sid, n_assembly, n_plasmid, 'no_assembly_records' if not n_assembly else ('no_candidate_records' if not n_plasmid else 'candidates_present')])
                db.commit()
            n_features = db.execute('SELECT count(*) FROM refs').fetchone()[0]
            with (stage / 'reference.fasta').open('w') as stream:
                for fid, dna in db.execute('SELECT feature_id, dna FROM refs ORDER BY feature_id'):
                    stream.write('>' + fid + '\n')
                    for start in range(0, len(dna), 80):
                        stream.write(dna[start:start + 80] + '\n')
            write_tsv(stage / 'features.tsv', ['feature_id', 'length_bp', 'is_plasmid', 'sequence_sha256', 'source_count', 'plasmid_source_count'],
                      ([fid, length, int(n_plasmid > 0), fid[4:], n_sources, n_plasmid] for fid, length, n_sources, n_plasmid in db.execute('''
                        SELECT r.feature_id, r.length_bp, count(*), sum(s.is_plasmid)
                        FROM refs r JOIN sources s USING(feature_id) GROUP BY r.feature_id ORDER BY r.feature_id''')))
            write_tsv(stage / 'sources.tsv', ['sample_id', 'contig_id', 'feature_id', 'orientation', 'is_plasmid_in_source'],
                      db.execute('SELECT sample_id, contig_id, feature_id, orientation, is_plasmid FROM sources ORDER BY sample_id, contig_id'))
            write_tsv(stage / 'samples.tsv', ['sample_id', 'assembly_records', 'plasmid_records', 'status'], sample_rows)
        (stage / 'working.sqlite').unlink()
        manifest = {'schema_version': 1, 'identity': 'complete nucleotide identity modulo reverse complement; uppercase IUPAC DNA',
                    'plasmid_membership': 'candidate in at least one source sample; source-specific calls retained',
                    'features': n_features, 'samples': len(sample_ids), 'inputs': input_files,
                    'files_sha256': {name: file_digest(stage / name) for name in ['reference.fasta', 'features.tsv', 'sources.tsv', 'samples.tsv']},
                    'limitations': ['not ANI/plasmid family clustering or circular rotation normalization', 'different fragments or near homologues remain separate competitive references']}
        (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        stage.rename(output)
    except BaseException:
        shutil.rmtree(stage)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sample-ids', nargs='+', required=True)
    parser.add_argument('--assemblies', nargs='+', type=Path, required=True)
    parser.add_argument('--plasmids', nargs='+', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--expected-samples', type=int)
    args = parser.parse_args()
    try:
        build(args.sample_ids, args.assemblies, args.plasmids, args.out_dir, args.expected_samples)
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(2, str(error) + '\n')
