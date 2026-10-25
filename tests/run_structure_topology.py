#!/usr/bin/env python3
"""Actual structure/report wrappers on locked topology references and controls.

Requires R/Biostrings/data.table and Nextflow. Fetch the two exact references
listed in structure-reference.lock.json, then provide their directory. Reference
bytes and metadata are checked before running. No classifier or read inference.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sequences(path):
    records = {}
    for line in path.read_text().splitlines():
        if line.startswith('>'):
            key = line[1:].split()[0]
            assert key not in records
            records[key] = ''
        else:
            records[key] += line.strip().upper()
    return records


def run(base, references):
    lock = json.loads((ROOT / 'tests/structure-reference.lock.json').read_text())
    dna = {}
    for ref in lock['references']:
        accession = ref['accession']
        for suffix, digest in ref['files'].items():
            assert sha(references / (accession + '.' + suffix)) == digest
        gb = (references / (accession + '.gb')).read_text()
        assert re.search(r'\b' + ref['topology'] + r'\b', gb.splitlines()[0])
        assert re.search(r'^VERSION\s+' + re.escape(accession) + r'\b', gb, re.M)
        seq = ''.join(re.findall('[a-zA-Z]+', gb.split('ORIGIN')[1].split('//')[0])).upper()
        assert sequences(references / (accession + '.fasta')) == {accession: seq}
        assert len(seq) == ref['length']
        assert hashlib.sha256(seq.encode()).hexdigest() == ref['sequence_sha256']
        dna[accession] = seq
    fixture = base / 'fixtures'
    fixture.mkdir()
    shutil.copyfile(references / 'NC_003903.1.fasta', fixture / 'SCP1.fasta')
    shutil.copyfile(references / 'NC_007941.1.fasta', fixture / 'pUTI89.fasta')
    (fixture / 'metadata_circle.fasta').write_text('>NC_007941.1 topology=circular\n' + dna['NC_007941.1'] + '\n')
    rng = random.Random(3661)
    head = ''.join(rng.choices('ACGT', k=25))
    body = 'A' + ''.join(rng.choices('ACGT', k=798)) + 'A'
    rc = head.translate(str.maketrans('ACGT', 'TGCA'))[::-1]
    (fixture / 'mixed.fasta').write_text('>itr\n' + head + body + rc + '\n>dtr\n' + head + body + head + '\n')
    (fixture / 'empty.fasta').write_text('')
    (fixture / 'samples.tsv').write_text('sample_id\nSCP1\npUTI89\nmetadata_circle\nmixed\nempty\n')
    sources = ['bin/plasmid_structure.R', 'bin/generate_report.R', 'assets/plasmid_report.Rmd',
               'modules/detection/structure.nf', 'modules/cross_sample/report.nf',
               'tests/nextflow/structure_topology.nf', 'tests/run_structure_topology.py',
               'tests/structure-reference.lock.json']
    initial = {name: sha(ROOT / name) for name in sources}
    fixture_hashes = {p.name: sha(p) for p in fixture.iterdir()}
    config = base / 'native.config'
    config.write_text("process.executor='local'\nprocess.cpus=1\nprocess.memory='1 GB'\n"
                      "process.maxForks=1\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\n"
                      "params.publish_dir_mode='copy'\n")
    out = base / 'out'
    params = {'outdir': str(out), 'fixture_dir': str(fixture), 'report_only': False,
              'platform': 'assembly', 'project_name': 'topology_reference_controls'}
    runs = []
    env = os.environ.copy()
    env['PATH'] = str(ROOT / 'bin') + ':' + env['PATH']

    def invoke(name, report_only):
        directory = base / name
        directory.mkdir()
        params['report_only'] = report_only
        param_file = directory / 'params.json'
        param_file.write_text(json.dumps(params))
        cmd = [shutil.which('nextflow') or 'nextflow', '-C', str(config), 'run',
               str(ROOT / 'tests/nextflow/structure_topology.nf'), '-params-file', str(param_file),
               '-work-dir', str(directory / 'work'), '-with-trace', str(directory / 'trace.tsv'), '-ansi-log', 'false']
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        (directory / 'stdout.log').write_text(result.stdout)
        (directory / 'stderr.log').write_text(result.stderr)
        tasks = list(csv.DictReader((directory / 'trace.tsv').open(), delimiter='\t')) if (directory / 'trace.tsv').exists() else []
        runs.append({'name': name, 'command': cmd, 'exit': result.returncode, 'tasks': tasks})
        assert result.returncode == 0, result.stdout + result.stderr
        assert len(tasks) == (1 if report_only else 5)
        assert all(t['status'] == 'COMPLETED' and t['exit'] == '0' for t in tasks)

    invoke('structure', False)
    rows = {}
    for sid in ['SCP1', 'pUTI89', 'metadata_circle', 'mixed', 'empty']:
        table = out / '04_plasmid_detection/structure' / (sid + '.plasmid_structure.tsv')
        reader = csv.DictReader(table.open(), delimiter='\t')
        rows[sid] = list(reader)
        assert reader.fieldnames[-3:] == ['repeat_type', 'topology_status', 'topology_evidence']
        original = sequences(fixture / (sid + '.fasta'))
        assert {r['plasmid_id'] for r in rows[sid]} == set(original)
        assert all(r['sample_id'] == sid and int(r['length_bp']) == len(original[r['plasmid_id']]) for r in rows[sid])
    scp = rows['SCP1'][0]
    assert (scp['is_circular'], scp['method'], scp['terminal_overlap_bp'], scp['repeat_type'], scp['topology_status'], scp['topology_evidence']) == ('false', 'itr', '1000', 'itr', 'unknown', 'none')
    assert (rows['pUTI89'][0]['is_circular'], rows['pUTI89'][0]['topology_status']) == ('false', 'unknown')
    assert (rows['metadata_circle'][0]['is_circular'], rows['metadata_circle'][0]['method']) == ('true', 'header_marker')
    assert [(r['is_circular'], r['method']) for r in rows['mixed']] == [('false', 'itr'), ('true', 'dtr')]
    assert rows['empty'] == []
    # Isolated, explicit assembly of report inputs after producer completion.
    consensus = out / '04_plasmid_detection/consensus'
    consensus.mkdir()
    for sid in rows:
        shutil.copyfile(fixture / (sid + '.fasta'), consensus / (sid + '.plasmid_contigs.fasta'))
        (consensus / (sid + '.plasmid_consensus.tsv')).write_text('contig_id\tsample_id\tplasmid_call\tsupporting_tools\n' + ''.join(r['plasmid_id'] + '\t' + sid + '\tplasmid\tcontrolled_input\n' for r in rows[sid]))
    invoke('report', True)
    report = (out / 'report/report.md').read_text()
    expected = {'SCP1': (1, 0), 'pUTI89': (1, 0), 'metadata_circle': (1, 1), 'mixed': (2, 1), 'empty': (0, 0)}
    for sid, (total, circular) in expected.items():
        assert f'| {sid} | {total} | {circular} |' in report
    assert 'unknown topology, not confirmed linearity' in report
    assert initial == {name: sha(ROOT / name) for name in sources}
    assert fixture_hashes == {p.name: sha(p) for p in fixture.iterdir()}
    receipt = {'pass': True, 'runs': runs, 'source_sha256': initial, 'fixture_sha256': fixture_hashes,
               'reference_lock': lock, 'expected_counts': expected, 'observed_structure': rows,
               'limitations': ['Known linear SCP1 plus circular pUTI89 reference metadata; no classifier, topology sensitivity benchmark, graph/read confirmation, container or nf-test certification.',
                               'REPORT is invoked only after explicitly preparing isolated completed inputs; production publishDir synchronization TA-015 is not tested or fixed.']}
    (base / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('PASS: five structure tasks, one actual REPORT task; IDs, lengths, repeats, unknown/candidate semantics and counts checked.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', required=True)
    parser.add_argument('--references', required=True)
    args = parser.parse_args()
    base = Path(args.work_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)
    run(base, Path(args.references).resolve())
