#!/usr/bin/env python3
"""Native complete bacterial reference index gate controls; no read reduction."""
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
    parser.add_argument('--assembly', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(exist_ok=False, parents=True)
    root = Path(__file__).resolve().parents[1]
    helper = root / 'bin/medaka_index_resources.py'
    assembly = args.assembly.resolve(strict=True)
    paths = [assembly, Path(str(assembly) + '.fai'), Path(str(assembly) + '.map-ont.mmi')]
    source_before = {str(p): sha(p) for p in paths}
    draft = out / 'draft.fasta'
    for suffix in ['', '.fai', '.map-ont.mmi']:
        shutil.copy2(Path(str(assembly) + suffix), Path(str(draft) + suffix))
    runs = []
    env = dict(os.environ, PATH=str(Path(sys.prefix) / 'bin') + ':' + os.environ['PATH'],
               PYTHONDONTWRITEBYTECODE='1')

    def run(name, expected=0, expect=None, source=draft):
        output = out / (name + '.json')
        command = [sys.executable, str(helper), '--assembly', str(source),
                   '--output', str(output), '--threads', '2']
        if expect:
            command += ['--expect', str(expect)]
        result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=300)
        (out / (name + '.stdout')).write_text(result.stdout)
        (out / (name + '.stderr')).write_text(result.stderr)
        runs.append({'case': name, 'command': command, 'returncode': result.returncode,
                     'receipt': str(output) if output.exists() else None})
        assert (result.returncode == 0) == (expected == 0), (name, result.stderr)
        assert output.exists() == (expected == 0)
        print(name, result.returncode, flush=True)
        return output

    baseline = run('baseline')
    run('unchanged', expect=baseline)
    for suffix, offset, name in [('.map-ont.mmi', 0, 'mmi-magic'),
                                 ('.map-ont.mmi', -20, 'mmi-internal'),
                                 ('.fai', 0, 'fai-id'),
                                 ('', 200, 'reference-base')]:
        target = Path(str(draft) + suffix)
        original = target.read_bytes()
        before = target.stat()
        data = bytearray(original)
        if not suffix:
            # A change between ambiguous symbols can produce the same packed
            # index. Use a definite A/C/G/T substitution in the full reference.
            offset = next(i for i in range(200, len(data)) if data[i] in b'ACGT')
            data[offset] = ord('C') if data[offset] == ord('A') else ord('A')
        else:
            data[offset] ^= 1
        target.write_bytes(data)
        os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
        assert target.stat().st_size == before.st_size and target.stat().st_mtime_ns == before.st_mtime_ns
        try:
            run(name, expected=1)
            assert 'differs from native reference rebuild' in (out / (name + '.stderr')).read_text()
        finally:
            target.write_bytes(original)
            os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
        run(name + '-restored', expect=baseline)
    missing = out / 'no-adjacent'
    missing.mkdir()
    absent_draft = missing / 'draft.fasta'
    shutil.copy2(assembly, absent_draft)
    receipt = run('absent-indexes', source=absent_draft)
    assert json.loads(receipt.read_text())['adjacent'] == {'.fai': None, '.gzi': None, '.map-ont.mmi': None}
    assert list(missing.iterdir()) == [absent_draft], 'Probe wrote to source directory'
    target = Path(str(draft) + '.map-ont.mmi')
    original = target.read_bytes()
    before = target.stat()
    # Replace only a disposable test index with a dangling link.
    target.unlink()
    target.symlink_to(out / 'missing-index')
    try:
        run('dangling-index', expected=1)
    finally:
        target.unlink()
        target.write_bytes(original)
        os.chmod(target, before.st_mode)
        os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
    run('final-restored', expect=baseline)
    assert source_before == {str(p): sha(p) for p in paths}
    report = {'formal_acceptance': False, 'production_gate': False, 'pass_bounded_checks': True,
              'source_sha256': {str(p.relative_to(root)): sha(p) for p in [helper, Path(__file__).resolve()]},
              'original_resources_unchanged': True, 'actual_cli_cases': len(runs), 'runs': runs,
              'scope': 'Full bacterial reference; fixed native canonical index generation each successful capture. Same-size/mtime MMI magic/internal, FAI and reference mutation refusal; byte restoration identity; missing indexes/no source writes; dangling index refusal. No model/inference/cache/production wiring or RLE/force/OCI acceptance.'}
    (out / 'run.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
