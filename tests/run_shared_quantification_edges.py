#!/usr/bin/env python3
"""Actual mapping boundary cases: tie ambiguity, empty reference, missing sample.

Two deliberately near-identical reference variants share every read interval.
They are controlled variants of locked pUTI89 DNA, not biological truth labels.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream, delimiter='\t'))


def run(base, reference, bowtie, coverm, python_prefix):
    lock = json.loads((ROOT / 'tests/structure-reference.lock.json').read_text())['references'][1]
    assert hashlib.sha256(reference.read_bytes()).hexdigest() == lock['files']['fasta']
    dna = ''.join(reference.read_text().splitlines()[1:])
    variant = dna[:90000] + ('A' if dna[90000] != 'A' else 'C') + dna[90001:]
    complement = str.maketrans('ACGT', 'TGCA')
    rc = lambda seq: seq.translate(complement)[::-1]
    runs = []
    sources = ['bin/build_shared_catalogue.py', 'bin/collect_shared_abundance.py', 'subworkflows/shared_quantification.nf',
               'modules/cross_sample/shared_catalogue.nf', 'modules/cross_sample/shared_abundance.nf', 'conf/shared_quantification.config',
               'tests/nextflow/shared_quantification_edges.nf', 'tests/run_shared_quantification_edges.py']
    hashes = {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in sources}
    for case in ['ambiguous', 'empty', 'missing_sample']:
        p = base / case
        p.mkdir()
        fixture = p / 'fixtures'
        fixture.mkdir()
        for sid, seq in {'A': dna, 'B': variant, 'C': rc(dna), 'D': ''}.items():
            f = fixture / sid
            f.mkdir()
            text = '>NODE_1\n' + seq + '\n' if seq and case != 'empty' else ''
            (f / 'assembly.fasta').write_text(text)
            (f / 'plasmids.fasta').write_text(text if sid in ['A', 'B'] else '')
            for mate in [1, 2]:
                parts = []
                for i in range(20):
                    start = 15000 + i * 700
                    read = dna[start:start + 150] if mate == 1 else rc(dna[start + 350:start + 500])
                    # Both catalogue variants match these reads exactly.
                    assert (read in dna or rc(read) in dna) and (read in variant or rc(read) in variant)
                    if sid == 'D':
                        read = 'N' * 150
                    parts.append(f'@{sid}_{i}/{mate}\n{read}\n+\n' + 'I' * 150 + '\n')
                (f / f'R{mate}.fastq').write_text(''.join(parts))
        config = p / 'native.config'
        config.write_text(f"includeConfig '{ROOT}/conf/shared_quantification.config'\n"
            "process.executor='local'\nprocess.cpus=1\nprocess.memory='1 GB'\nprocess.maxForks=1\n"
            "conda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\nparams.publish_dir_mode='copy'\n"
            "process {\n" + f"withName: 'COVERM_SHARED' {{ beforeScript = 'export PATH=\"{coverm}/bin:$PATH\"' }}\n"
            + f"withName: 'SHARED_CATALOGUE|SHARED_ABUNDANCE_TABLES' {{ beforeScript = 'export PATH=\"{python_prefix}/bin:$PATH\"' }}\n}}\n")
        config.write_text(config.read_text().replace("\n}\n", f"\nwithName: 'SAMTOOLS_VIEW_SHARED' {{ beforeScript = 'export PATH=\"{coverm}/bin:$PATH\"' }}\n}}\n"))
        params = {'outdir': str(p / 'out'), 'fixture_dir': str(fixture), 'read_ids': ['A', 'B', 'C'] if case == 'missing_sample' else ['A', 'B', 'C', 'D']}
        (p / 'params.json').write_text(json.dumps(params))
        cmd = [shutil.which('nextflow') or 'nextflow', '-C', str(config), 'run', str(ROOT / 'tests/nextflow/shared_quantification_edges.nf'),
               '-params-file', str(p / 'params.json'), '-work-dir', str(p / 'work'), '-with-trace', str(p / 'trace.tsv'), '-ansi-log', 'false']
        env = os.environ.copy()
        env['PATH'] = str(bowtie / 'bin') + ':' + env['PATH']
        result = subprocess.run(cmd, env=env, text=True, capture_output=True)
        (p / 'stdout.log').write_text(result.stdout)
        (p / 'stderr.log').write_text(result.stderr)
        tasks = rows(p / 'trace.tsv') if (p / 'trace.tsv').exists() else []
        if case == 'missing_sample':
            assert result.returncode != 0
            diagnostics = ''.join(q.read_text() for q in (p / 'work').rglob('.command.err'))
            assert 'missing/unexpected sample measurement' in diagnostics
            assert not list((p / 'out/tables').rglob('*.tsv'))
        else:
            assert result.returncode == 0, result.stdout + result.stderr
            assert len(tasks) == (2 if case == 'empty' else 15), len(tasks)
            assert all(t['status'] == 'COMPLETED' and t['exit'] == '0' for t in tasks)
            measured = rows(p / 'out/tables/contig_abundance.tsv')
            assert len(measured) == (0 if case == 'empty' else 8)
            assert all(r['raw_count'] == '0' and float(r['coverage']) == 0 for r in measured)
            states = rows(p / 'out/tables/sample_states.tsv')
            assert {r['sample_id'] for r in states} == {'A', 'B', 'C', 'D'}
            assert all(r['quantification_status'] == ('empty_catalogue' if case == 'empty' else 'measured_zero') for r in states)
        runs.append({'case': case, 'command': cmd, 'exit': result.returncode, 'tasks': tasks,
                     'checks': 'ambiguous low-MAPQ primary assignments excluded; globally empty catalogue explicit all-sample status; missing sample fails without final quantification publication'})
        assert hashes == {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in sources}
        (base / 'run.json').write_text(json.dumps({'pass': True, 'runs': runs, 'source_sha256': hashes,
            'limits': ['short mapper boundary controls only; not near-homologue sensitivity, wet-lab truth, full platform, image or nf-test certification']}, indent=2) + '\n')
        print('PASS', case, len(tasks), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', required=True)
    parser.add_argument('--reference', required=True)
    parser.add_argument('--bowtie-prefix', required=True)
    parser.add_argument('--coverm-prefix', required=True)
    parser.add_argument('--python-prefix', required=True)
    args = parser.parse_args()
    base = Path(args.work_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)
    run(base, Path(args.reference).resolve(), Path(args.bowtie_prefix).resolve(), Path(args.coverm_prefix).resolve(), Path(args.python_prefix).resolve())
