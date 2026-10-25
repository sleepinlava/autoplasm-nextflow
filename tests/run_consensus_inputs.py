#!/usr/bin/env python3
"""Native consensus/structure contract checks with controlled inputs, no classifier inference."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def read_fasta(path):
    records = {}
    key = None
    for line in path.read_text().splitlines():
        if line.startswith('>'):
            key = line[1:].split()[0]
            assert key not in records
            records[key] = ''
        else:
            records[key] += line
    return records


def run_checks(base):
    fixture = base / 'fixtures'
    fixture.mkdir()
    dna = 'ACGT' * 300
    expected = {'genomad': {'p1': dna}, 'platon': {'p1': dna}, 'negative': {}, 'empty': {}, 'plasx': {'p1': dna}}
    for sid in [*expected, 'legacy', 'foreign', 'empty-record']:
        assembly = '>p1 original header\n' + dna + '\n'
        summary = 'seq_name\tplasmid_score\n'
        if sid in ['genomad', 'platon']:
            summary += 'p1\t0.99\n'
        if sid == 'plasx':
            assembly += '>p2\n' + dna + '\n'
            (fixture / (sid + '.plasx.tsv')).write_text('contig\tscore\np1\t0.99\np2\t1e-8\n')
        if sid == 'empty':
            assembly = ''
        if sid == 'empty-record':
            assembly = '>p1\n'
        if sid == 'foreign':
            summary += 'foreign\t0.99\n'
        (fixture / (sid + '.assembly.fa')).write_text(assembly)
        (fixture / (sid + '.genomad.tsv')).write_text(summary)
        if sid == 'platon':
            (fixture / (sid + '.platon.tsv')).write_text('contig_id\tclassification\np1\tplasmid\n')
        if sid == 'legacy':
            (fixture / (sid + '.scapp.fasta')).write_text('>RNODE_1\n' + dna + '\n')
    config = base / 'native.config'
    config.write_text("params.consensus_method='weighted_vote'\n"
                      "params.consensus_weights='genomad:0.6,platon:0.4,plasx:1'\n"
                      "params.publish_dir_mode='copy'\nprocess.executor='local'\n"
                      "process.cpus=1\nprocess.memory='1 GB'\n"
                      "conda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\n")
    runs = []
    cases = [('positive', ','.join(expected), None),
             ('legacy', 'legacy', 'SCAPP support has been removed'),
             ('foreign', 'foreign', 'Unresolved prediction ID'),
             ('empty-record', 'empty-record', 'Empty FASTA sequence')]
    for case, ids, error in cases:
        p = base / case
        p.mkdir()
        (p / 'params.json').write_text(json.dumps({'fixture_dir': str(fixture), 'ids': ids,
                                                 'outdir': str(p / 'out')}))
        command = [shutil.which('nextflow') or 'nextflow', '-C', str(config), 'run',
                   str(ROOT / 'tests/nextflow/consensus_inputs.nf'), '-params-file',
                   str(p / 'params.json'), '-work-dir', str(p / 'work'),
                   '-with-trace', str(p / 'trace.tsv'), '-ansi-log', 'false']
        env = os.environ.copy()
        env['PATH'] = str(ROOT / 'bin') + ':' + env['PATH']
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        (p / 'stdout.log').write_text(result.stdout)
        (p / 'stderr.log').write_text(result.stderr)
        tasks = list(csv.DictReader((p / 'trace.tsv').open(), delimiter='\t')) if (p / 'trace.tsv').exists() else []
        if error:
            checks = {'nonzero': result.returncode != 0, 'diagnostic': error in result.stdout + result.stderr,
                      'one_failed_consumer': len(tasks) == 1 and tasks[0]['status'] == 'FAILED' and tasks[0]['exit'] == '2',
                      'no_published_files': not [f for f in (p / 'out').rglob('*') if f.is_file()]}
        else:
            checks = {'success': result.returncode == 0,
                      'ten_completed_tasks': len(tasks) == 10 and all(t['status'] == 'COMPLETED' and t['exit'] == '0' for t in tasks)}
            if checks['success']:
                for sid, sequences in expected.items():
                    out = p / 'out/04_plasmid_detection'
                    consensus = out / 'consensus' / (sid + '.plasmid_consensus.tsv')
                    rows = list(csv.DictReader(consensus.open(), delimiter='\t'))
                    structure = list(csv.DictReader((out / 'structure' / (sid + '.plasmid_structure.tsv')).open(), delimiter='\t'))
                    checks[sid + '_DNA'] = read_fasta(out / 'consensus' / (sid + '.plasmid_contigs.fasta')) == sequences
                    checks[sid + '_identity'] = {r['contig_id'] for r in rows if r['plasmid_call'] == 'plasmid'} == set(sequences)
                    checks[sid + '_structure'] = {r['plasmid_id'] for r in structure} == set(sequences) and all(int(r['length_bp']) == len(sequences[r['plasmid_id']]) for r in structure)
                    checks[sid + '_metrics'] = all(r['sample_id'] == sid and int(r['length']) == 1200 and float(r['gc_content']) == 0.5 and 'scapp' not in r for r in rows)
        runs.append({'case': case, 'command': command, 'exit': result.returncode, 'checks': checks, 'tasks': tasks})
        print(case, checks, flush=True)
        sources = ['bin/plasmid_consensus.R', 'bin/plasmid_structure.R', 'modules/detection/consensus.nf',
                   'modules/detection/structure.nf', 'tests/nextflow/consensus_inputs.nf', 'tests/run_consensus_inputs.py']
        receipt = {'runs': runs, 'pass': all(all(r['checks'].values()) for r in runs),
                   'source_sha256': {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in sources},
                   'limitations': ['controlled fixtures; native original R modules', 'no classifier inference, database/model, image, nf-test or full platform certification']}
        (base / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt['pass']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', required=True)
    args = parser.parse_args()
    base = Path(args.work_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)
    raise SystemExit(0 if run_checks(base) else 1)
