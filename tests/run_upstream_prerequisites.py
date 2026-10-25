#!/usr/bin/env python3
"""Check real fixed upstream archive helpers; discovery is a separate check."""
import argparse
import csv
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ['output', 'fasta', 'utility-prefix', 'pigz-prefix']:
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    base = args.output.resolve(); base.mkdir(exist_ok=False)
    fasta = args.fasta.resolve(); dna = fasta.read_bytes()
    assert dna.startswith(b'>') and dna.strip()
    utilities = args.utility_prefix.resolve(); pigz = args.pigz_prefix.resolve()
    env = {**os.environ, 'PATH': str(utilities / 'bin') + ':' + str(pigz / 'bin') + ':' + os.environ['PATH']}
    versions = {}
    for name, binary, expected in [('tar', utilities / 'bin/tar', '1.34'),
                                   ('gzip', utilities / 'bin/gzip', '1.13'),
                                   ('pigz', pigz / 'bin/pigz', '2.8')]:
        p = subprocess.run([str(binary), '--version'], capture_output=True, text=True, env=env)
        text = p.stdout + p.stderr
        pattern = r'tar \(GNU tar\) (\S+)' if name == 'tar' else name + r' (\S+)'
        match = re.fullmatch(pattern, text.splitlines()[0])
        assert p.returncode == 0 and match and match[1] == expected, (name, text)
        versions[name] = dict(binary=str(binary), reported=text.strip(),
                              sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
    golden = base / 'golden.fna.gz'; golden.write_bytes(gzip.compress(dna, mtime=0))
    corrupt = base / 'corrupt.fna.gz'; damaged = bytearray(golden.read_bytes()); damaged[-8] ^= 1; corrupt.write_bytes(damaged)
    archives = {}
    for kind, member in [('nested', 'bundle/reference.fna'), ('flat', 'reference.fna')]:
        archive = base / (kind + '.tar.gz')
        with tarfile.open(archive, 'w:gz') as stream:
            info = tarfile.TarInfo(member); info.size = len(dna); info.mtime = 0
            stream.addfile(info, io.BytesIO(dna))
        archives[kind] = archive
    config = base / 'config'
    config.write_text("process.executor='local'\nprocess.cpus=1\nprocess.memory='256 MB'\nprocess.errorStrategy='terminate'\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\ntrace.fields='task_id,hash,name,status,exit,workdir'\n")
    sources = [Path(__file__).resolve(), ROOT / 'tests/nextflow/upstream_archive_prerequisites.nf',
               *sorted((ROOT / 'tests/nf-test/prerequisites').rglob('*'))]
    sources = [p for p in sources if p.is_file()]
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    runs = []
    for case in ['positive', 'corrupt-gzip']:
        folder = base / case; folder.mkdir()
        params = dict(fasta=str(fasta), gzip=str(golden if case == 'positive' else corrupt),
                      nested_archive=str(archives['nested']), flat_archive=str(archives['flat']),
                      execute_other_tools=case == 'positive')
        pf = folder / 'params.json'; pf.write_text(json.dumps(params, indent=2) + '\n')
        cmd = [str(ROOT / 'results/tool-audit/runtime/bin/nextflow'), '-C', str(config), 'run',
               str(ROOT / 'tests/nextflow/upstream_archive_prerequisites.nf'), '-params-file', str(pf),
               '-work-dir', str(folder / 'work'), '-with-trace', str(folder / 'trace.tsv'), '-ansi-log', 'false']
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=180)
        (folder / 'stdout').write_text(p.stdout); (folder / 'stderr').write_text(p.stderr)
        tasks = list(csv.DictReader((folder / 'trace.tsv').open(), delimiter='\t'))
        if case == 'positive':
            assert p.returncode == 0 and len(tasks) == 4 and all(t['status'] == 'COMPLETED' for t in tasks), (p.stdout, p.stderr, tasks)
            assert {t['name'].split(' (', 1)[0] for t in tasks} == {'GUNZIP', 'PIGZ_COMPRESS', 'UNTAR_NESTED', 'UNTAR_FLAT'}
            for task in tasks:
                work = Path(task['workdir']); name = task['name']
                if name.startswith('GUNZIP '):
                    assert (work / 'golden.fna').read_bytes() == dna
                elif name.startswith('PIGZ_COMPRESS '):
                    assert gzip.decompress((work / (fasta.name + '.gz')).read_bytes()) == dna
                else:
                    label = 'nested' if name.startswith('UNTAR_NESTED ') else 'flat'
                    files = [q for q in (work / label).rglob('*') if q.is_file()]
                    assert [q.name for q in files] == ['reference.fna'] and files[0].read_bytes() == dna
            assert all(marker in p.stdout for marker in ['DECODED=decoded:preserved:', 'COMPRESSED=compressed:preserved:', 'NESTED=nested:preserved:', 'FLAT=flat:preserved:'])
        else:
            assert p.returncode != 0 and len(tasks) == 1 and tasks[0]['status'] == 'FAILED' and tasks[0]['name'].startswith('GUNZIP ')
            error = (Path(tasks[0]['workdir']) / '.command.err').read_text()
            assert 'crc error' in error and 'DECODED=' not in p.stdout, error
        runs.append(dict(case=case, command=cmd, exit_code=p.returncode, tasks=tasks, checks_passed=True))
    unchanged = before == {str(p.relative_to(ROOT)): sha(p) for p in sources}
    input_unchanged = fasta.read_bytes() == dna
    assert unchanged and input_unchanged
    record = dict(runs=runs, source_sha256=before, source_unchanged=unchanged,
                  input_unchanged=input_unchanged,
                  input=dict(path=str(fasta), sha256=sha(fasta), bytes=len(dna)), actual_tools=versions,
                  scope='Four actual fixed-source helper tasks preserve complete original fixture bytes/meta; native CRC failure propagates. Declared tar1.34/gzip1.13 and existing pigz2.8 binaries, local backend; not the ten complete upstream suites, containers, inference, or biological accuracy.')
    record['pass'] = True
    (base / 'run.json').write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
