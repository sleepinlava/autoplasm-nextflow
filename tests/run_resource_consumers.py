#!/usr/bin/env python3
"""Actual consumer cache keys, with explicit node stubs/version observers, never inference."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess

from module_harness import run_session_uuid

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ['MOB_db', 'BAKTA_db', 'AMR_db', 'RGI_card', 'RGI_wildcard', 'EGG_db', 'EGG_data',
             'META_db', 'KRAKEN_db', 'GTDB_db', 'CHECK_db', 'BLAST_db', 'MACSY_models', 'DAS_db', 'PHF_db']
PROCESSES = {name.split('_')[0] for name in RESOURCES}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(base, only_resource=None):
    selected = [only_resource] if only_resource else RESOURCES
    assert all(name in RESOURCES for name in selected)
    base.mkdir(parents=True, exist_ok=False)
    fixture = base / 'fixture'
    fixture.mkdir()
    paths = {}
    for name in RESOURCES:
        folder = fixture / name
        (folder / 'metadata').mkdir(parents=True)
        (folder / 'metadata/metadata.txt').write_text('VERSION_DATA=EXPLICIT_CACHE_OBSERVER\n')
        (folder / '.signal\ncache').write_bytes(b'old\n')
        paths[name] = str(folder)
    fasta = fixture / 'input.fna'
    fasta.write_text('>CACHE_OBSERVER\nACGTACGTACGT\n')
    bins = fixture / 'bins.tsv'
    bins.write_text('CACHE_OBSERVER\tSTUB_ONLY\n')
    observer = base / 'observer-bin'
    observer.mkdir()
    script = '''#!/bin/sh
case "$(basename "$0")" in
  plasmidhostfinder.py) printf 'scope\\tresult\\nEXPLICIT_CACHE_OBSERVER\\tNO_INFERENCE\\n' > observer.tsv ;;
  amrfinder) printf '2026-01-01.1 EXPLICIT_CACHE_OBSERVER\\n' ;;
  DAS_Tool) printf 'DAS Tool EXPLICIT_CACHE_OBSERVER\\n' ;;
  hmmsearch) printf '# EXPLICIT_CACHE_OBSERVER\\n# HMMER EXPLICIT_CACHE_OBSERVER\\n' ;;
  *) printf 'EXPLICIT_CACHE_OBSERVER\\n' ;;
esac
'''
    for name in ['mob_typer', 'bakta', 'amrfinder', 'rgi', 'kma', 'python', 'metaphlan', 'kraken2',
                 'pigz', 'gtdbtk', 'checkm2', 'blastn', 'macsyfinder', 'hmmsearch', 'DAS_Tool',
                 'plasmidhostfinder.py']:
        path = observer / name
        path.write_text(script)
        path.chmod(0o755)
    config = base / 'config'
    config.write_text("process.executor='local'\nprocess.cpus=1\nprocess.memory='128 MB'\n"
                      "process.maxForks=3\nprocess.errorStrategy='terminate'\n"
                      "conda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\n"
                      "params.publish_dir_mode='copy'\ntrace.fields='task_id,hash,name,status,exit,workdir'\n")
    params = base / 'params.json'
    params.write_text(json.dumps({'fasta': str(fasta), 'bins': str(bins), 'resources': paths,
                                 'outdir': str(base / 'out')}) + '\n')
    sources = ['lib/ResourceIdentity.groovy', 'lib/resource_inputs.nf',
               'tests/nextflow/resource_consumer_cache.nf', 'tests/run_resource_consumers.py']
    sources += [str(path.relative_to(ROOT)) for path in ROOT.glob('modules/nf-core/**/main.nf')
                if 'val(db_identity)' in path.read_text() or 'val(card_identity)' in path.read_text()
                or 'val(models_identity)' in path.read_text() or 'val(eggnog_data_identity)' in path.read_text()]
    sources += ['modules/host/plasmidhostfinder.nf']
    hashes = {name: sha(ROOT / name) for name in sources}
    env = dict(os.environ, PATH=str(observer) + ':' + os.environ['PATH'])
    records = []
    session = None
    cold_hashes = {}
    for case in ['cold', 'unchanged'] + [phase + ':' + resource for resource in selected for phase in ['mutated', 'restored']]:
        folder = base / case.replace(':', '-')
        folder.mkdir()
        if ':' in case:
            phase, resource = case.split(':')
            target = Path(paths[resource]) / '.signal\ncache'
            before = target.stat()
            parent = target.parent.stat()
            target.write_bytes(b'new\n' if phase == 'mutated' else b'old\n')
            os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
            os.utime(target.parent, ns=(parent.st_atime_ns, parent.st_mtime_ns))
        trace = folder / 'trace.tsv'
        command = [str(ROOT / 'results/tool-audit/runtime/bin/nextflow'), '-C', str(config), 'run',
                   str(ROOT / 'tests/nextflow/resource_consumer_cache.nf'), '-params-file', str(params),
                   '-work-dir', str(base / 'work'), '-with-trace', str(trace), '-ansi-log', 'false', '-stub-run']
        command += ['-resume', session] if session else ['-name', 'resource_consumers_cold']
        result = subprocess.run(command, env=env, cwd=base, capture_output=True, text=True, timeout=180)
        (folder / 'stdout').write_text(result.stdout)
        (folder / 'stderr').write_text(result.stderr)
        tasks = list(csv.DictReader(trace.open(), delimiter='\t')) if trace.exists() else []
        entry = {'case': case, 'command': command, 'exit_code': result.returncode, 'tasks': tasks}
        records.append(entry)
        (base / 'progress.json').write_text(json.dumps(records, indent=2) + '\n')
        assert result.returncode == 0, result.stdout + result.stderr
        assert len(tasks) == len(PROCESSES) == 13, tasks
        observed = {task['name'].split(' (')[0]: task for task in tasks}
        assert set(observed) == PROCESSES, observed
        affected = case.split(':')[1].split('_')[0] if case.startswith('mutated:') else None
        for name, task in observed.items():
            expected = 'COMPLETED' if case == 'cold' or name == affected else 'CACHED'
            assert task['status'] == expected, (case, name, task)
            if case == 'cold':
                cold_hashes[name] = task['hash']
            else:
                assert (task['hash'] != cold_hashes[name]) == (name == affected), (case, task)
        if session is None:
            session = run_session_uuid('resource_consumers_cold', base)
        print(case, 'passed', flush=True)
    assert hashes == {name: sha(ROOT / name) for name in sources}
    (base / 'run.json').write_text(json.dumps({
        'pass': True, 'runs': records, 'source_sha256': hashes, 'session_uuid': session, 'mutated_resource_inputs':selected,
        'scope': str(len(selected))+' selected mutation inputs across13actual stub consumers; synthetic LF/hidden byte changes, '
                 'per-node stub/version observers and one PHF CLI observer. No biological classifier/model inference.'
    }, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--only-resource',choices=RESOURCES)
    args=parser.parse_args()
    run(args.work_dir.resolve(),args.only_resource)
