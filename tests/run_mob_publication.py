#!/usr/bin/env python3
"""Verify actual MOB wrapper publication with explicit output-protocol doubles.

No native MOB classification, package readiness or biological accuracy claim.
The old config control must miss all publication. The repair must publish cached
and cold outputs without collisions and survive removal of private task work.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--before-config', type=Path, required=True)
    parser.add_argument('--nextflow', type=Path, required=True)
    args = parser.parse_args()
    base = args.output.resolve()
    base.mkdir(exist_ok=False)
    bindir = base / 'observer-bin'
    bindir.mkdir()
    observer = bindir / 'mob_recon'
    observer.write_text('''#!/usr/bin/env python3
import argparse,json,pathlib,sys
if '--version' in sys.argv:
 print('mob_recon 3.1.9');raise SystemExit(0)
p=argparse.ArgumentParser();p.add_argument('--infile');p.add_argument('--outdir');p.add_argument('--sample_id');p.add_argument('--num_threads');p.add_argument('--observer-empty',action='store_true');a=p.parse_args()
d=pathlib.Path(a.outdir);d.mkdir();dna=pathlib.Path(a.infile).read_bytes()
(d/'chromosome.fasta').write_bytes(dna)
(d/'contig_report.txt').write_text('sample_id\\tobserver_only\\n'+a.sample_id+'\\ttrue\\n')
if not a.observer_empty:
 (d/'plasmid_1.fasta').write_bytes(dna)
 (d/'mobtyper_results.txt').write_text('sample_id\\tobserver_only\\n'+a.sample_id+'\\ttrue\\n')
pathlib.Path('observer.json').write_text(json.dumps({'observer_only':True,'sample_id':a.sample_id,'arguments':sys.argv,'dna_hex':dna.hex()}))
''')
    observer.chmod(0o755)
    python_observer = bindir / 'python3'
    python_observer.write_text('#!' + sys.executable + '\n' + (ROOT / 'tests/mock_e2e/mock_python.py').read_text().split('\n',1)[1])
    python_observer.chmod(0o755)
    records = []
    for sid, empty, dna in [('A', False, 'ACGT' * 40), ('A__B.v1', True, 'TGCA' * 53)]:
        fasta = base / (sid + '.fa')
        fasta.write_text('>shared_id\n' + dna + '\n')
        records.append({'id': sid, 'empty': empty, 'fasta': str(fasta)})
    sources = ['conf/nfcore_downstream.config', 'modules/nf-core/mobsuite/recon/main.nf', 'tests/nextflow/mob_publication.nf', 'tests/run_mob_publication.py', 'tests/mock_e2e/mock_python.py', 'bin/mobsuite_preflight.py', 'lib/mobsuite_runtime.nf']
    hashes = {path: sha(ROOT / path) for path in sources}
    runs = []
    work = base / 'work'
    key = 'mob_publish_' + hashlib.sha256(str(base).encode()).hexdigest()[:12]

    def execute(name, domain_config, resume=False):
        folder = base / name
        folder.mkdir()
        config = folder / 'config'
        config.write_text("params.publish_dir_mode='copy'\nincludeConfig " + repr(str(domain_config.resolve())) + '''
process.executor='local'
process.cpus=1
process.memory='512 MB'
process.errorStrategy='terminate'
process { withName: 'MOB_SUITE_ANNOT|MOB_RECON' { ext.args = { meta.observer_empty ? '--observer-empty' : '' } } }
conda.enabled=false
docker.enabled=false
podman.enabled=false
singularity.enabled=false
''')
        (folder / 'params.json').write_text(json.dumps({'records': records, 'outdir': str(folder / 'out')}, indent=2) + '\n')
        command = [str(args.nextflow.resolve()), '-C', str(config), 'run', str(ROOT / 'tests/nextflow/mob_publication.nf'), '-params-file', str(folder / 'params.json'),
                   '-work-dir', str(work), '-with-trace', str(folder / 'trace.tsv'), '-ansi-log', 'false'] + (['-resume', key] if resume else ['-name', key])
        env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ['PATH'])
        with (folder / 'stdout.log').open('w') as stdout, (folder / 'stderr.log').open('w') as stderr:
            process = subprocess.run(command, env=env, cwd=ROOT, stdout=stdout, stderr=stderr)
        with (folder / 'trace.tsv').open() as stream:
            tasks = list(csv.DictReader(stream, delimiter='\t'))
        checks = {'native_wrapper_success': process.returncode == 0, 'four_tasks': len(tasks) == 4,
                  'exact_status': all(row['status'] == ('CACHED' if resume else 'COMPLETED') and row['exit'] == '0' for row in tasks)}
        snapshots = {}
        if name == 'before':
            checks['original_publication_missing'] = not (folder / 'out').exists()
        else:
            for stage in ['08_annotation/mob_suite', '05_plasmid_binning/mob_recon']:
                for record in records:
                    destination = folder / 'out' / stage / record['id']
                    files = {path.name: path for path in destination.rglob('*') if path.is_file()}
                    expected = {'chromosome.fasta', 'contig_report.txt'} | (set() if record['empty'] else {'plasmid_1.fasta', 'mobtyper_results.txt'})
                    checks[stage + '/' + record['id'] + '/files'] = set(files) == expected
                    checks[stage + '/' + record['id'] + '/DNA'] = all(files[name].read_bytes() == Path(record['fasta']).read_bytes() for name in expected if name.endswith('.fasta'))
                    checks[stage + '/' + record['id'] + '/identity'] = all(record['id'] + '\ttrue\n' in files[name].read_text() for name in expected if name.endswith('.txt'))
                    snapshots.update({str(path): sha(path) for path in files.values()})
            checks['not_symlinks'] = all(not Path(path).is_symlink() for path in snapshots)
        row = {'case': name, 'command': command, 'exit_code': process.returncode, 'tasks': tasks, 'checks': checks, 'published_sha256': snapshots, 'pass': all(checks.values())}
        runs.append(row)
        (base / 'runs-progress.json').write_text(json.dumps(runs, indent=2) + '\n')
        assert row['pass'], row
        print(name, row['pass'], flush=True)

    execute('before', args.before_config)
    execute('current-resume', ROOT / 'conf/nfcore_downstream.config', resume=True)
    work = base / 'cold-work'
    key += '_cold'
    execute('current-cold', ROOT / 'conf/nfcore_downstream.config')
    # Only this harness's two private work directories; keep trace, logs and
    # observer execution records before testing final-output independence.
    evidence = base / 'task-evidence'
    for directory in [base / 'work', base / 'cold-work']:
        for path in directory.rglob('*'):
            if path.is_file() and path.name in ['.command.sh', '.command.run', '.command.out', '.command.err', '.exitcode', 'observer.json']:
                saved = evidence / directory.name / path.relative_to(directory)
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, saved)
        shutil.rmtree(directory)
    assert all(sha(path) == value for row in runs for path, value in row['published_sha256'].items())
    assert hashes == {path: sha(ROOT / path) for path in sources}
    (base / 'run.json').write_text(json.dumps({'pass': True, 'runs': runs, 'source_sha256': hashes,
        'private_work_removed': True, 'published_outputs_survive_cleanup': True,
        'limitations': ['Actual production module shell/alias/config/publish behavior only; mob_recon is an explicit output-protocol observer. No MOB installation, classification or biological accuracy certification.', 'One nonempty and one optional-empty sample share local contig ID but have different DNA; stages and sample directories are separate.', '4 original completed +4 current cached +4 current cold entries are not12 independent scientific samples.']}, indent=2) + '\n')


if __name__ == '__main__':
    main()
