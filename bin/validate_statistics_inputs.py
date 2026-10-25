#!/usr/bin/env python3
"""Validate the full cohort and measured state before any cross-sample analysis."""
import argparse
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
from collect_shared_abundance import read_rows, number


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): result.update(chunk)
    return result.hexdigest()


def canonical_decimal(value):
    # Decimal.normalize() rounds to the active context precision. Identity must
    # retain every supplied digit, while accepting equivalent forms and +/-0.
    if value.is_zero(): return '0'
    sign, digits, exponent = value.as_tuple()
    digits = list(digits)
    while digits[-1] == 0:
        digits.pop(); exponent += 1
    return str(sign) + ':' + ''.join(map(str, digits)) + 'e' + str(exponent)


def validate(contigs, plasmids, states, metadata, expected_samples, output):
    _, cohort = read_rows(metadata)
    ids = [r.get('sample_id', '') for r in cohort]
    if not ids or any(not sid.strip() for sid in ids) or len(ids) != len(set(ids)):
        raise ValueError('Metadata needs unique nonempty sample_id')
    if len(ids) != expected_samples: raise ValueError('Metadata expected sample count mismatch')
    fields, statuses = read_rows(states)
    required = ['sample_id', 'reference_features', 'plasmid_features', 'eligible_read_alignments', 'plasmid_read_alignments', 'quantification_status']
    if not set(required) <= set(fields): raise ValueError('Missing sample-state fields')
    state = {r['sample_id']: r for r in statuses}
    if len(state) != len(statuses) or set(state) != set(ids): raise ValueError('Quantification state sample set mismatch')
    for row in state.values():
        for field in required[1:-1]: row[field] = int(number(row[field], 'state:' + field, True))
        expected = 'empty_catalogue' if row['reference_features'] == 0 else 'measured_zero' if row['eligible_read_alignments'] == 0 else 'measured'
        if row['quantification_status'] != expected: raise ValueError('Quantification state/value mismatch')
    if output.exists(): raise ValueError('Refusing preexisting statistics validation output')
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.statistics-', dir=output.parent))
    database = stage / 'measurement-index.sqlite'
    connection = sqlite3.connect(database)
    connection.execute('PRAGMA journal_mode=OFF')
    connection.execute('PRAGMA cache_size=-4096')
    connection.execute('PRAGMA temp_store=FILE')
    connection.execute('CREATE TABLE measurements (role TEXT, sample TEXT, feature TEXT, count TEXT, coverage TEXT, PRIMARY KEY(role,sample,feature)) WITHOUT ROWID')
    summaries = {}
    try:
        for role, path, feature_column, nfield, cfield in [('contigs', contigs, 'contig_id', 'reference_features', 'eligible_read_alignments'), ('plasmids', plasmids, 'plasmid_id', 'plasmid_features', 'plasmid_read_alignments')]:
            totals = dict.fromkeys(ids, 0)
            with path.open() as stream:
                reader = csv.DictReader(stream, delimiter='\t')
                fields = reader.fieldnames or []
                required_columns = {feature_column, 'sample_id', 'coverage', 'raw_count'}
                if len(fields) != len(set(fields)) or not required_columns <= set(fields): raise ValueError(role + ': missing/duplicate measurement columns')
                for row in reader:
                    if None in row or any(row.get(field) is None for field in required_columns): raise ValueError(role + ': malformed measurement row')
                    sid, fid = row['sample_id'], row[feature_column]
                    if sid not in state or not fid.strip(): raise ValueError(role + ': unexpected/empty sample-feature identity')
                    count = int(number(row['raw_count'], role + ':' + sid + ':' + fid, True))
                    coverage = canonical_decimal(Decimal(number(row['coverage'], role + ':' + sid + ':' + fid)))
                    try: connection.execute('INSERT INTO measurements VALUES (?,?,?,?,?)', (role,sid,fid,str(count),str(coverage)))
                    except sqlite3.IntegrityError: raise ValueError(role + ': duplicate sample-feature measurement') from None
                    totals[sid] += count
            feature_count = connection.execute('SELECT count(DISTINCT feature) FROM measurements WHERE role=?',(role,)).fetchone()[0]
            for sid in ids:
                n = connection.execute('SELECT count(*) FROM measurements WHERE role=? AND sample=?',(role,sid)).fetchone()[0]
                if n != feature_count or n != state[sid][nfield]: raise ValueError(role + ': incomplete sample-feature rectangle or declared feature count mismatch; missing is not zero')
                if totals[sid] != state[sid][cfield]: raise ValueError(role + ': count total differs from measured state')
            summaries[role] = {'features':feature_count,'samples':len(ids)}
        mismatch = connection.execute("SELECT 1 FROM measurements p LEFT JOIN measurements c ON c.role='contigs' AND c.sample=p.sample AND c.feature=p.feature WHERE p.role='plasmids' AND (c.feature IS NULL OR p.count!=c.count OR p.coverage!=c.coverage) LIMIT 1").fetchone()
        if mismatch: raise ValueError('Plasmid subset measurement differs from contig reference')
        connection.close(); database.unlink()
        for path, name in [(contigs, 'contig_abundance.tsv'), (plasmids, 'plasmid_abundance.tsv'), (metadata, 'samples.tsv'), (states, 'sample_states.tsv')]:
            shutil.copyfile(path, stage / name)
        (stage / 'validation.json').write_text(json.dumps({'status': 'validated', 'sample_ids': sorted(ids), 'tables': summaries,
            'input_sha256': {str(p): digest(p) for p in [contigs, plasmids, states, metadata]},
            'empty_semantics': 'Empty feature sets require producer state0; measured zeros remain full-cohort rows; missing producers/measurements fail'}, indent=2) + '\n')
        stage.rename(output)
    except BaseException:
        connection.close()
        shutil.rmtree(stage); raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['contigs', 'plasmids', 'states', 'metadata', 'out-dir']: p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--expected-samples', type=int, required=True)
    a = p.parse_args()
    try: validate(a.contigs, a.plasmids, a.states, a.metadata, a.expected_samples, a.out_dir)
    except (ValueError, KeyError, OSError) as error: p.exit(2, str(error) + '\n')
