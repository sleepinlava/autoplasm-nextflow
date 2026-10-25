#!/usr/bin/env python3
"""Actual RGI queries against two full, fixed CARD releases, using native dependencies."""
from module_harness import render_module_harness
from pathlib import Path
import argparse
import csv
import hashlib
import json
import os
import random
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def gene_hits(path):
    result = []
    for value in json.loads(path.read_text()).values():
        if isinstance(value, dict):
            result += [hit for hit in value.values() if isinstance(hit, dict) and 'ARO_name' in hit]
    return result


def run_checks(base, fixture, prefix, module, cases):
    assert json.loads((fixture / 'card-3.3.0/card.json').read_text())['_version'] == '3.3.0'
    assert json.loads((fixture / 'global-3.2.8/card.json').read_text())['_version'] == '3.2.8'
    global_sha = hashlib.sha256((fixture / 'global-3.2.8/card.json').read_bytes()).hexdigest()
    local_sha = hashlib.sha256((fixture / 'card-3.3.0/card.json').read_bytes()).hexdigest()
    rng = random.Random(729)
    (base / 'negative.fasta').write_text('>controlled_random_DNA\n' + ''.join(rng.choices('ACGT', k=1600)) + '\n')
    (base / 'empty-global').mkdir()
    bad = base / 'fixture-mislabelled-card'
    bad.mkdir()
    shutil.copyfile(fixture / 'card-3.3.0/card.json', bad / 'card.json')
    for tail in ['', '_all']:
        shutil.copyfile(fixture / ('card-3.3.0/card_database_v3.3.0' + tail + '.fasta'), bad / ('card_database_v9.9.9' + tail + '.fasta'))
    probe = base / 'probe.nf'
    text = (ROOT / 'tests/nextflow/rgi_database_scope.nf').read_text()
    probe.write_text(render_module_harness(ROOT/'tests/nextflow/rgi_database_scope.nf', '../../modules/nf-core/rgi/main/main', module, 'validate_rgi_card.py'))
    runs = []
    expected = {'VIM77': ('VIM-77', '6038'), 'GENOME': ('mphE', '2614')}
    for case, ids, card, global_db, error in [
        ('with-global', ['VIM77', 'GENOME', 'NEGATIVE'], fixture / 'card-3.3.0', fixture / 'global-3.2.8', None),
        ('upstream-oracle', ['GENOME'], fixture / 'card-3.3.0', fixture / 'global-3.2.8', None),
        ('without-global', ['VIM77'], fixture / 'card-3.3.0', base / 'empty-global', None),
        ('mislabelled-card', ['VIM77'], bad, fixture / 'global-3.2.8', 'Missing CARD annotation file')
    ]:
        if cases and case not in cases:
            continue
        p = base / case
        p.mkdir()
        config = p / 'config'
        config.write_text("includeConfig '" + str(ROOT / 'conf/nfcore_downstream.config') + "'\n"
                          "params.publish_dir_mode='copy'\nprocess.executor='local'\nprocess.cpus=1\n"
                          "process.memory='2 GB'\nprocess.maxForks=1\nconda.enabled=false\n"
                          "docker.enabled=false\nsingularity.enabled=false\n"
                          "env.DB_PATH='" + str(global_db) + "'\nenv.DATA_PATH='" + str(global_db) + "'\n")
        if case == 'upstream-oracle':
            with config.open('a') as stream:
                stream.write("process { withName: 'RGI' { ext.args2='--clean --include_loose --include_nudge --low_quality --debug' } }\n")
        records = [{'id': sid, 'fasta': str(base / 'negative.fasta' if sid == 'NEGATIVE' else fixture / ('NC_020818.1.fasta' if sid == 'GENOME' else 'VIM77.fasta'))} for sid in ids]
        (p / 'params.json').write_text(json.dumps({'records': records, 'card': str(card), 'outdir': str(p / 'out')}))
        command = [shutil.which('nextflow') or 'nextflow', '-C', str(config), 'run', str(probe),
                   '-params-file', str(p / 'params.json'), '-work-dir', str(p / 'work'),
                   '-with-trace', str(p / 'trace.tsv'), '-ansi-log', 'false']
        env = os.environ.copy()
        env['PATH'] = str(prefix / 'bin') + ':' + env['PATH']
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        (p / 'stdout.log').write_text(result.stdout)
        (p / 'stderr.log').write_text(result.stderr)
        tasks = list(csv.DictReader((p / 'trace.tsv').open(), delimiter='\t')) if (p / 'trace.tsv').exists() else []
        if error:
            checks = {'nonzero': result.returncode != 0, 'diagnostic': error in result.stdout + result.stderr,
                      'one_failed_task': len(tasks) == 1 and tasks[0]['status'] == 'FAILED',
                      'no_published_files': not [f for f in (p / 'out').rglob('*') if f.is_file()],
                      'query_not_started': not list((p / 'work').rglob('localDB'))}
        else:
            versions = re.findall(r'^DB_VERSION_CAPTURE=(.*)$', result.stdout, re.M)
            checks = {'success': result.returncode == 0, 'completed_tasks': len(tasks) == len(ids) and all(t['status'] == 'COMPLETED' and t['exit'] == '0' for t in tasks),
                      'actual_version_emitted': versions == ['3.3.0'] * len(ids)}
            if checks['success']:
                for sid in ids:
                    out = p / 'out/08_annotation/rgi'
                    hits = gene_hits(out / (sid + '.rgi.json'))
                    rows = list(csv.DictReader((out / (sid + '.rgi.txt')).open(), delimiter='\t'))
                    if sid == 'NEGATIVE':
                        checks[sid + '_no_hits'] = not hits and not rows
                    else:
                        name, model = ('NDM-1', '783') if case == 'upstream-oracle' else expected[sid]
                        checks[sid + '_perfect_exact_model'] = any(h['ARO_name'] == name and str(h['model_id']) == model and h['type_match'] == 'Perfect' and float(h['perc_identity']) == 100 for h in hits)
                        checks[sid + '_table_identity'] = any(r['Best_Hit_ARO'] == name and r['Model_ID'] == model and r['Cut_Off'] == 'Perfect' and float(r['Best_Identities']) == 100 for r in rows)
                    if sid == 'GENOME':
                        checks[sid + '_msrE_perfect'] = any(h['ARO_name']=='msrE' and str(h['model_id'])=='33' and h['type_match']=='Perfect' and float(h['perc_identity'])==100 for h in hits)
                    # The copy actually loaded into each task must be the declared CARD.
                loaded = list((p / 'work').rglob('localDB/card.json'))
                checks['loaded_JSON_is_declared'] = len(loaded) == len(ids) and all(hashlib.sha256(q.read_bytes()).hexdigest() == local_sha for q in loaded)
        checks['global_CARD_unchanged'] = hashlib.sha256((fixture / 'global-3.2.8/card.json').read_bytes()).hexdigest() == global_sha
        runs.append({'case': case, 'command': command, 'exit': result.returncode, 'checks': checks, 'tasks': tasks})
        print(case, checks, flush=True)
        receipt = {'runs': runs, 'pass': all(all(r['checks'].values()) for r in runs),
                   'source_sha256': {str(Path(str(module) + '.nf')): hashlib.sha256(Path(str(module) + '.nf').read_bytes()).hexdigest(),
                                     'tests/run_rgi_database_scope.py': hashlib.sha256((ROOT / 'tests/run_rgi_database_scope.py').read_bytes()).hexdigest()},
                   'card_sha256': {'local_3.3.0': local_sha, 'global_3.2.8': global_sha},
                   'limitations': ['real native RGI6.0.8 + declared KMA1.6.11, full genuine CARD3.3.0 vs3.2.8',
                                   'VIM-77 is exact reference sanity control, random DNA is controlled negative; not an AMR sensitivity/clinical phenotype benchmark',
                                   'fixed upstream real plasmid, original module/config; no nf-test/image or full platform certification']}
        (base / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt['pass']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', required=True, type=Path)
    parser.add_argument('--fixture-dir', required=True, type=Path)
    parser.add_argument('--prefix', required=True, type=Path)
    parser.add_argument('--module', type=Path, default=ROOT / 'modules/nf-core/rgi/main/main')
    parser.add_argument('--cases', default='')
    args = parser.parse_args()
    base = args.work_dir.resolve()
    base.mkdir(parents=True, exist_ok=True)
    raise SystemExit(0 if run_checks(base, args.fixture_dir.resolve(), args.prefix.resolve(), args.module.resolve(), args.cases.split(',') if args.cases else []) else 1)
