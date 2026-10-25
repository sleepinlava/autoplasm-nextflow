#!/usr/bin/env python3
"""Real native RGI through the original annotation subworkflow, with optional selection controls."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
from run_rgi_database_scope import ROOT, gene_hits


def run_checks(base, fixture, prefix):
    runs = []
    for case, tools in [('enabled', [' rgi ']), ('disabled', [])]:
        p = base / case
        p.mkdir()
        config = p / 'config'
        config.write_text("includeConfig '" + str(ROOT / 'conf/nfcore_downstream.config') + "'\n"
                          "params.publish_dir_mode='copy'\nprocess.executor='local'\nprocess.cpus=1\n"
                          "process.memory='2 GB'\nprocess.maxForks=1\nconda.enabled=false\n"
                          "docker.enabled=false\nsingularity.enabled=false\n"
                          "env.DB_PATH='" + str(fixture / 'global-3.2.8') + "'\n"
                          "env.DATA_PATH='" + str(fixture / 'global-3.2.8') + "'\n")
        records = [{'id': 'VIM77', 'fasta': str(fixture / 'VIM77.fasta')},
                   {'id': 'GENOME', 'fasta': str(fixture / 'NC_020818.1.fasta')}]
        params = {'records': records, 'card_db': str(fixture / 'card-3.3.0'), 'outdir': str(p / 'out'),
                  'annotation_optional_tools': tools, 'annotation_tools': [], 'typing_tools': [],
                  'typing_optional_tools': [], 'plasmid_binning_tools': []}
        (p / 'params.json').write_text(json.dumps(params))
        command = [shutil.which('nextflow') or 'nextflow', '-C', str(config), 'run', str(ROOT / 'tests/nextflow/rgi_downstream.nf'),
                   '-params-file', str(p / 'params.json'), '-work-dir', str(p / 'work'), '-with-trace', str(p / 'trace.tsv'), '-ansi-log', 'false']
        env = os.environ.copy()
        env['PATH'] = str(prefix / 'bin') + ':' + env['PATH']
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        (p / 'stdout.log').write_text(result.stdout)
        (p / 'stderr.log').write_text(result.stderr)
        tasks = list(csv.DictReader((p / 'trace.tsv').open(), delimiter='\t')) if (p / 'trace.tsv').exists() else []
        out = p / 'out/08_annotation/rgi'
        checks = {'success': result.returncode == 0, 'task_count': len(tasks) == (2 if tools else 0),
                  'only_RGI_completed': all(t['name'].startswith('PLASMID_DOWNSTREAM:RGI') and t['status'] == 'COMPLETED' and t['exit'] == '0' for t in tasks),
                  'published_result_names': {f.name for f in out.glob('*')} == ({sid + '.rgi.' + ext for sid in ['VIM77', 'GENOME'] for ext in ['json', 'txt']} if tools else set())}
        if result.returncode == 0 and tools:
            for sid, name, model in [('VIM77', 'VIM-77', '6038'), ('GENOME', 'mphE', '2614')]:
                hits = gene_hits(out / (sid + '.rgi.json'))
                checks[sid + '_exact_model'] = any(h['ARO_name'] == name and str(h['model_id']) == model and h['type_match'] == 'Perfect' and float(h['perc_identity']) == 100 for h in hits)
            source_sha = hashlib.sha256((fixture / 'card-3.3.0/card.json').read_bytes()).hexdigest()
            copies = list((p / 'work').rglob('localDB/card.json'))
            checks['each_sample_loaded_declared_CARD'] = len(copies) == 2 and all(hashlib.sha256(f.read_bytes()).hexdigest() == source_sha for f in copies)
        runs.append({'case': case, 'command': command, 'exit': result.returncode, 'checks': checks, 'tasks': tasks})
        print(case, checks, flush=True)
        receipt = {'runs': runs, 'pass': all(all(r['checks'].values()) for r in runs),
                   'source_sha256': {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in ['modules/nf-core/rgi/main/main.nf', 'bin/validate_rgi_card.py', 'subworkflows/plasmid_downstream.nf', 'conf/nfcore_downstream.config', 'tests/run_rgi_downstream.py', 'tests/nextflow/rgi_downstream.nf']},
                   'limitations': ['original subworkflow/native real RGI and two fixed genuine CARD releases, not observers', 'exact reference sanity and locked real plasmid only; no image/nf-test/full-platform or AMR performance certification']}
        (base / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt['pass']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--fixture-dir', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    args = parser.parse_args()
    base = args.work_dir.resolve()
    base.mkdir(parents=True, exist_ok=True)
    raise SystemExit(0 if run_checks(base, args.fixture_dir.resolve(), args.prefix.resolve()) else 1)
