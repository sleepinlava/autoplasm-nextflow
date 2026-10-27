#!/usr/bin/env python3
"""Fixed 2.1.6 native regression using the complete original upstream positive fixture.

Uses the production module and shared downstream configuration. This bounded
regression does not establish resource-aware cache identity or OCI readiness.
"""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess

from module_harness import run_session_uuid

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sequences(path):
    records = []
    for line in path.read_text().splitlines():
        if line.startswith('>'):
            records.append('')
        elif line.strip():
            assert records, path
            records[-1] += line.strip().upper()
    return records


def run(base, prefix, upstream):
    base.mkdir(parents=True, exist_ok=False)
    fixture = upstream / 'test/test.fsa'
    golden = upstream / 'test/test_results.tsv'
    assert fixture.stat().st_size == 569 and list(map(len, sequences(fixture))) == [540]
    sources = ['modules/nf-core/plasmidfinder/main.nf',
               'modules/nf-core/plasmidfinder/environment.yml',
               'conf/nfcore_downstream.config', 'tests/mock_e2e/mock_tool.py',
               'tests/nextflow/plasmidfinder_native.nf', 'tests/run_plasmidfinder_native.py']
    before = {p: sha(ROOT / p) for p in sources}
    assert 'conda-forge::python=3.10' in (ROOT / sources[1]).read_text()
    env = dict(os.environ, PATH=str(prefix / 'bin') + ':' + os.environ['PATH'],
               PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
    # The interpreter and dependencies are real; this check does not replace the solver lock.
    version = subprocess.run([str(prefix / 'bin/python'), '-c',
                              'import sys; from distutils.spawn import find_executable; '
                              'assert sys.version_info[:2] == (3,10); print(sys.version)'],
                             capture_output=True, text=True, env=env, check=True)
    (base / 'python.stdout').write_text(version.stdout)
    (base / 'python.stderr').write_text(version.stderr)
    compressed = base / 'test.fsa.gz'
    compressed.write_bytes(gzip.compress(fixture.read_bytes(), mtime=0))
    config = base / 'config'
    config.write_text("includeConfig '" + str(ROOT / 'conf/nfcore_downstream.config') + "'\n"
                      "params.outdir='" + str(base / 'out') + "'\n"
                      "params.publish_dir_mode='copy'\n"
                      "process { executor='local';cpus=1;memory='1 GB';errorStrategy='terminate';maxRetries=0 }\n"
                      "conda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\n"
                      "trace.fields='task_id,hash,name,status,exit,workdir'\n")
    legacy = base / 'legacy.config'
    legacy.write_text("includeConfig '" + str(config) + "'\n"
                      "process { withName: 'PLASMIDFINDER' { ext.args='--legacy' } }\n")
    runs = []
    suffixes = ['.json', '.txt', '.tsv', '-hit_in_genome_seq.fsa', '-plasmid_seqs.fsa']
    def execute(name, fasta, expected, resume=None, stub=False, selected_config=config):
        case = base / name
        case.mkdir()
        cmd = [str(ROOT / 'results/tool-audit/runtime/bin/nextflow'), '-C', str(selected_config),
               'run', str(ROOT / 'tests/nextflow/plasmidfinder_native.nf'),
               '--fasta', str(fasta), '-work-dir', str(base / 'work'),
               '-with-trace', str(case / 'trace.tsv'), '-ansi-log', 'false']
        cmd += ['-resume', resume] if resume else ['-name', 'plasmidfinder_' + name.replace('-', '_')]
        if stub:
            cmd.append('-stub-run')
        proc = subprocess.run(cmd, cwd=base, env=env, capture_output=True, text=True, timeout=180)
        (case / 'stdout').write_text(proc.stdout)
        (case / 'stderr').write_text(proc.stderr)
        tasks = list(csv.DictReader((case / 'trace.tsv').open(), delimiter='\t'))
        record = dict(case=name, command=cmd, exit_code=proc.returncode, tasks=tasks)
        runs.append(record)
        (base / 'progress.json').write_text(json.dumps(runs, indent=2) + '\n')
        assert len(tasks) == 1 and tasks[0]['status'] == expected, record
        assert (proc.returncode == 0) == (expected != 'FAILED'), record
        work = Path(tasks[0]['workdir'])
        shell = (work / '.command.sh').read_text()
        if expected == 'FAILED':
            assert 'unrecognized arguments: --legacy' in (work / '.command.log').read_text()
            record['native_unsupported_flag_reproduced'] = True
        else:
            outputs = {s: work / ('positive.plasmidfinder' + s) for s in suffixes}
            assert all(p.is_file() for p in outputs.values())
            if stub:
                assert all(p.stat().st_size == 0 for p in outputs.values())
                record['scope'] = 'stub output interface only'
            else:
                assert '--legacy' not in shell
                assert outputs['.tsv'].read_bytes() == golden.read_bytes()
                assert sequences(outputs['-hit_in_genome_seq.fsa']) == sequences(fixture)
                assert sequences(outputs['-plasmid_seqs.fsa']) == sequences(fixture)
                data = json.loads(outputs['.json'].read_text())['plasmidfinder']
                assert data['user_input']['method'] == 'blast' and data['user_input']['file_format'] == 'fasta'
                hit = next(iter(data['results']['Enterobacteriaceae']['enterobacteriaceae'].values()))
                assert hit['identity'] == 100 and hit['coverage'] == 100
                assert hit['HSP_length'] == hit['template_length'] == 540
                assert hit['positions_in_contig'] == '1..540' and hit['accession'] == 'AF250878'
                assert all(v == 'No hit found' for v in data['results']['Gram Positive'].values())
                assert len(data['results']['Gram Positive']) == 8
                record.update(full_original_golden_tsv_equal=True, full_hit_and_reference_dna_equal=True,
                              all_nine_default_database_results_checked=True,
                              output_sha256={s: sha(p) for s, p in outputs.items()})
        print(name, expected, flush=True)
        return tasks[0]
    execute('legacy-cli', fixture, 'FAILED', selected_config=legacy)
    cold = execute('cold', fixture, 'COMPLETED')
    session = run_session_uuid('plasmidfinder_cold', base)
    cached = execute('unchanged', fixture, 'CACHED', resume=session)
    assert cold['hash'] == cached['hash']
    execute('compressed', compressed, 'COMPLETED')
    execute('stub', fixture, 'COMPLETED', stub=True)
    after = {p: sha(ROOT / p) for p in sources}
    assert before == after
    result = dict(pass_bounded_checks=True, formal_acceptance=False,
                  scope='native production module with shared config: full original 569-byte/540bp software positive, '
                        'nine default DB groups, old CLI failure, plain/gzip, unchanged cache and separate stub; '
                        'no resource mutation/environment/OCI/all-platform acceptance',
                  source_sha256=after, fixture_sha256=sha(fixture), golden_sha256=sha(golden), runs=runs)
    (base / 'run.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--upstream', type=Path, required=True)
    args = parser.parse_args()
    run(args.output.resolve(), args.prefix.resolve(), args.upstream.resolve())
