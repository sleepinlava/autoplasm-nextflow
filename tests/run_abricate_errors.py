#!/usr/bin/env python3
"""Original vs guarded1.0.1 real pipeline failure and legitimate zero controls."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def run(base, prefix, fixture):
    base.mkdir(parents=True, exist_ok=False)
    helper = ROOT / 'bin/abricate_runtime_resources.pl'
    sources = ['tests/run_abricate_errors.py', 'bin/abricate_runtime_resources.pl']
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p:sha(ROOT / p) for p in sources}
    runs = []
    modes = ['converter-failure', 'blast-failure', 'legitimate-zero']
    for mode in modes:
        case = base / mode
        tools = case / 'tools'
        tools.mkdir(parents=True)
        env = dict(os.environ, PATH=str(tools) + ':' + str(prefix / 'bin') + ':' + os.environ['PATH'])
        if mode != 'legitimate-zero':
            tool = 'any2fasta' if mode == 'converter-failure' else 'blastn'
            original = str(prefix / 'bin' / tool)
            text = '#!/bin/bash\n'
            if tool == 'blastn':
                text += 'if [[ "$1" == "-version" ]]; then exec "' + original + '" "$@"; fi\n'
            text += '"' + original + '" "$@"\nexit ' + ('7' if tool == 'any2fasta' else '9') + '\n'
            wrapper = tools / tool
            wrapper.write_text(text)
            wrapper.chmod(0o755)
            sequence = fixture
        else:
            sequence = case / 'explicit-valid-zero.fa'
            sequence.write_text('>EXPLICIT_VALID_ZERO_CONTROL\n' + 'ACGT' * 64 + '\n')
        native = [str(sequence), '--db', 'ncbi', '--threads', '2']
        original_cmd = [str(prefix / 'bin/abricate'), *native]
        old = subprocess.run(original_cmd, env=env, capture_output=True, text=True, timeout=60)
        (case / 'original.tsv').write_text(old.stdout)
        (case / 'original.stderr').write_text(old.stderr)
        identity = case / 'identity.json'
        probe_cmd = [str(prefix / 'bin/perl'), str(helper), '--runtime-base64', 'e30=', '--output', str(identity), '--', *native]
        probe = subprocess.run(probe_cmd, env=env, capture_output=True, text=True, timeout=60)
        (case / 'probe.stderr').write_text(probe.stderr)
        assert probe.returncode == 0, probe.stderr
        new_cmd = [str(prefix / 'bin/perl'), str(helper), '--runtime-base64', 'e30=', '--verify', str(identity), '--execute', '--', *native]
        current = subprocess.run(new_cmd, env=env, capture_output=True, text=True, timeout=60)
        (case / 'guarded.tsv').write_text(current.stdout)
        (case / 'guarded.stderr').write_text(current.stderr)
        assert old.returncode == 0, old.stderr
        old_rows = list(csv.DictReader(old.stdout.splitlines(), delimiter='\t'))
        new_rows = list(csv.DictReader(current.stdout.splitlines(), delimiter='\t'))
        if mode == 'legitimate-zero':
            assert current.returncode == 0 and not old_rows and not new_rows
            assert old.stdout == current.stdout
        else:
            assert len(old_rows) == 5
            assert current.returncode != 0 and 'ABRicate input converter/BLAST subprocess failed' in current.stderr
        runs.append(dict(case=mode,original_command=original_cmd,probe_command=probe_cmd,guarded_command=new_cmd,
                         original_exit=old.returncode,guarded_exit=current.returncode,original_hits=len(old_rows),guarded_hits=len(new_rows),
                         scope='Real converter/BLAST and full original fixture; explicit late-exit7/9 observer only' if mode!='legitimate-zero' else 'Explicit synthetic valid-zero control, not biological negative truth'))
    assert before == {p:sha(ROOT / p) for p in sources}
    source = (prefix / 'bin/abricate').read_bytes()
    patched = source.replace(b'open BLAST, "$cmd |";', b'''open BLAST, '-|', 'bash', '-o', 'pipefail', '-c', $cmd or err("Cannot start ABRicate search pipeline");''').replace(b'close BLAST;',b'''close BLAST or err("ABRicate input converter/BLAST subprocess failed (status $?)");''')
    (base / 'guarded-source.pl').write_bytes(patched)
    (base / 'run.json').write_text(json.dumps(dict(pass_checks=True,runs=runs,source_sha256=before,source_unchanged=True,
        effective_guarded_source_sha256=sha(base/'guarded-source.pl'),original_source_sha256=sha(prefix/'bin/abricate'),
        scope='Two exact1.0.1 Perl pipeline checks, argv/FindBin/defaults/scientific thresholds preserved. Late-failure observer wrappers pass full real output then exit7/9; do not call them native defective tool binaries or extra biological samples. Actual missing.nhr BLAST failure tested separately in production/cache suite.'),indent=2)+'\n')
    print('PASS: original/current real search+late failure controls and valid-zero',flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--prefix',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True)
    a=p.parse_args();run(a.out.resolve(),a.prefix.resolve(),a.fixture.resolve())
