#!/usr/bin/env python3
"""Actual REPORT/R Markdown inputs, late producer, stale output and resume checks.

Controlled detection files and a delayed shell writer are interface fixtures,
not a classifier or annotation benchmark. No published result is a report input.
"""
import argparse
import csv
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trace(path):
    with path.open() as stream:
        return list(csv.DictReader(stream, delimiter='\t'))


class Cells(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell = [], [], None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr': self.row = []
        if tag in ['td', 'th']: self.cell = ''

    def handle_data(self, data):
        if self.cell is not None: self.cell += data

    def handle_endtag(self, tag):
        if tag in ['td', 'th']:
            self.row.append(self.cell.strip()); self.cell = None
        if tag == 'tr' and self.row: self.rows.append(self.row)


def prepare(fixture, count=1):
    fixture.mkdir(parents=True, exist_ok=True)
    (fixture / 'samples.tsv').write_text('sample_id\nS.1\n001\n')
    for sid in ['S.1', '001']:
        folder = fixture / sid
        folder.mkdir(exist_ok=True)
        n = count if sid == 'S.1' else 0
        (folder / 'plasmids.fasta').write_text(''.join(f'>p{i}\nACGT\n' for i in range(n)))
        (folder / 'consensus.tsv').write_text('sample_id\tcontig_id\tplasmid_call\tsupporting_tools\n' + ''.join(f'{sid}\tp{i}\tplasmid\tcontrolled_input\n' for i in range(n)))
        (folder / 'structure.tsv').write_text('sample_id\tplasmid_id\tis_circular\n' + ''.join(f'{sid}\tp{i}\tfalse\n' for i in range(n)))


def check_report(out, count, late):
    products = ['report.md', 'report.html', 'methods.md', 'report_data.json', 'report_inputs.json']
    assert all((out / 'report' / name).is_file() for name in products)
    data = json.loads((out / 'report/report_data.json').read_text())
    assert data['samples'] == [{'sample_id': 'S.1', 'consensus_plasmids': count, 'circular': 0, 'detection_tools': 'controlled_input'},
                               {'sample_id': '001', 'consensus_plasmids': 0, 'circular': 0, 'detection_tools': ''}]
    annotation = next(r for r in data['sections'] if r['name'] == '08_annotation')
    assert annotation['present'] == late
    assert next(r for r in data['sections'] if r['name'] == '06_plasmid_typing')['status'] == 'not_observed'
    manifest = json.loads((out / 'report/report_inputs.json').read_text())
    producers = {r['producer'] for r in manifest['records']}
    assert ('LATE_OPTIONAL' in producers) == late
    for field in ['report.md', 'methods.md', 'report.html', 'report_data.json', 'report_inputs.json']:
        assert 'OLD_SAMPLE' not in (out / 'report' / field).read_text()
    parser = Cells(); parser.feed((out / 'report/report.html').read_text())
    for row in data['samples']:
        assert [row['sample_id'], str(row['consensus_plasmids']), '0', row['detection_tools']] in parser.rows
        assert f"| {row['sample_id']} | {row['consensus_plasmids']} | 0 | {row['detection_tools']} |" in (out / 'report/report.md').read_text()
    assert 'Reads were quality-filtered' not in data['methods']
    assert 'static, not runtime probes' in data['methods']
    return {name: sha(out / 'report' / name) for name in products}


def run(base):
    fixture = base / 'fixtures'
    prepare(fixture)
    config = base / 'native.config'
    config.write_text("process.executor='local'\nprocess.cpus=1\nprocess.memory='1 GB'\nprocess.maxForks=1\n"
                      "conda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\nparams.publish_dir_mode='copy'\n"
                      "trace.fields='task_id,hash,name,status,exit,submit,start,complete,workdir'\n")
    sources = ['bin/generate_report.R', 'modules/cross_sample/report.nf', 'lib/report_events.nf',
               'assets/plasmid_report.Rmd', 'tests/nextflow/report_inputs.nf', 'tests/run_report_inputs.py']
    hashes = {n: sha(ROOT / n) for n in sources}
    env = os.environ.copy(); env['PATH'] = str(ROOT / 'bin') + ':' + env['PATH']
    runs = []
    for case, late, fail, resume, expected_count in [('late', True, False, False, 1),
         ('resume_unchanged', True, False, True, 1), ('resume_changed', True, False, True, 2),
         ('disabled', False, False, False, 1), ('late_failure', True, True, False, 1)]:
        if case == 'resume_changed': prepare(fixture, 2)
        if case == 'disabled': prepare(fixture, 1)
        directory = base / case
        directory.mkdir()
        execution = base / ('late' if resume else case)
        out = execution / 'out'
        # Poison both real and empty result directories. These must not become
        # observations. Optional writer publication is deliberately disabled.
        stale = out / '04_plasmid_detection/consensus'
        stale.mkdir(parents=True, exist_ok=True)
        (stale / 'OLD_SAMPLE.plasmid_contigs.fasta').write_text('>old\nACGT\n')
        (out / '08_annotation').mkdir(exist_ok=True)
        (out / '06_plasmid_typing').mkdir(exist_ok=True)
        params = {'outdir': str(out), 'fixture_dir': str(fixture), 'run_late': late, 'fail_late': fail}
        (directory / 'params.json').write_text(json.dumps(params))
        cmd = [shutil.which('nextflow') or 'nextflow', '-C', str(config), 'run', str(ROOT / 'tests/nextflow/report_inputs.nf'),
               '-params-file', str(directory / 'params.json'), '-work-dir', str(execution / 'work'),
               '-with-trace', str(directory / 'trace.tsv'), '-ansi-log', 'false']
        if resume: cmd.append('-resume')
        result = subprocess.run(cmd, env=env, text=True, capture_output=True, cwd=base)
        (directory / 'stdout.log').write_text(result.stdout); (directory / 'stderr.log').write_text(result.stderr)
        tasks = trace(directory / 'trace.tsv') if (directory / 'trace.tsv').exists() else []
        if fail:
            assert result.returncode != 0
            assert 'deliberate-late-failure' in result.stdout + result.stderr
            assert not any(t['name'].endswith('REPORT (report)') for t in tasks)
            assert not (out / 'report/report_data.json').exists()
            products = {}
        else:
            assert result.returncode == 0, result.stdout + result.stderr
            report = next(t for t in tasks if t['name'].endswith('REPORT (report)'))
            if case == 'resume_unchanged': assert report['status'] == 'CACHED'
            else: assert report['status'] == 'COMPLETED'
            if case == 'resume_changed':
                assert next(t for t in tasks if t['name'] == 'LATE_OPTIONAL')['status'] == 'CACHED'
            if case == 'late':
                optional = next(t for t in tasks if t['name'] == 'LATE_OPTIONAL')
                assert report['start'] >= optional['complete']
            products = check_report(out, expected_count, late)
            assert 'render failed' not in ''.join(q.read_text() for q in (execution / 'work').rglob('.command.err'))
        runs.append({'case': case, 'command': cmd, 'exit': result.returncode, 'tasks': tasks, 'products_sha256': products,
                     'checks': 'current input identity/counts; late disabled publication still observed; old directories ignored; JSON/HTML/Markdown agree; resume cache tracks explicit content; optional failure prevents report'})
        assert hashes == {n: sha(ROOT / n) for n in sources}
        (base / 'run.json').write_text(json.dumps({'pass': True, 'runs': runs, 'source_sha256': hashes,
            'limitations': ['controlled detection files and delayed shell process, native R Markdown/report; no biological classifier/annotation inference',
                            'version evidence can contain static process declarations; complete CLI/database/model provenance TA-016 remains incomplete',
                            'native local backend/Nextflow26.10; no image/remote executor/nf-test certification']}, indent=2) + '\n')
        print('PASS', case, [(t['name'], t['status']) for t in tasks], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', required=True)
    args = parser.parse_args()
    base = Path(args.work_dir).resolve(); base.mkdir(parents=True, exist_ok=True)
    run(base)
