#!/usr/bin/env python3
"""Full bacterial read input and real selected model corruption/restore gate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reads', type=Path, required=True)
    parser.add_argument('--assembly', type=Path, required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[1]
    helper = root / 'bin/medaka_model_resources.py'
    source_model = args.model.resolve(strict=True)
    before = sha(source_model)
    model = out / source_model.name
    shutil.copy2(source_model, model)
    env = dict(os.environ, PATH=str(Path(sys.prefix) / 'bin') + ':' + os.environ['PATH'],
               OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', PYTHONDONTWRITEBYTECODE='1', CUDA_VISIBLE_DEVICES='')
    runs = []

    def run(name, expected=0, expect=None):
        target = out / (name + '.json')
        command = [sys.executable, str(helper), '--reads', str(args.reads.resolve(strict=True)),
                   '--assembly', str(args.assembly.resolve(strict=True)), '--output', str(target), '--threads', '2']
        if expect:
            command += ['--expect', str(expect)]
        command += ['--', '-m', str(model)]
        result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=300)
        (out / (name + '.stdout')).write_text(result.stdout)
        (out / (name + '.stderr')).write_text(result.stderr)
        runs.append({'case': name, 'command': command, 'returncode': result.returncode,
                     'receipt': str(target) if target.exists() else None})
        assert (result.returncode == 0) == (expected == 0), (name, result.stderr)
        assert target.exists() == (expected == 0)
        print(name, result.returncode, flush=True)
        return target

    baseline = run('baseline')
    run('unchanged', expect=baseline)
    data = model.read_bytes()
    original = model.stat()
    damaged = bytearray(data)
    damaged[-1] ^= 1
    model.write_bytes(damaged)
    os.utime(model, ns=(original.st_atime_ns, original.st_mtime_ns))
    assert model.stat().st_size == original.st_size and model.stat().st_mtime_ns == original.st_mtime_ns
    try:
        run('corrupt-trailer', expected=1)
        assert 'Incorrect length of data produced' in (out / 'corrupt-trailer.stderr').read_text()
    finally:
        model.write_bytes(data)
        os.utime(model, ns=(original.st_atime_ns, original.st_mtime_ns))
    run('restored', expect=baseline)
    assert sha(source_model) == before and sha(model) == before
    report = {'pass_bounded_checks': True, 'formal_acceptance': False, 'production_gate': False,
              'actual_cli_cases': len(runs), 'runs': runs, 'original_model_unchanged': True,
              'source_sha256': {str(p.relative_to(root)): sha(p) for p in
                                [helper, root / 'bin/medaka_model_selection.py', Path(__file__).resolve()]},
              'scope': 'Complete bacterial reads/draft and full original model copied privately; native selection/compatibility/weight load, unchanged identity, same-size/mtime damaged gzip trailer refusal and restored identity. No inference or production cache/OCI/RLE certificate.'}
    (out / 'run.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
