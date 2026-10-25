#!/usr/bin/env python3
"""Positive native products and counterfactual corruption controls for the independent oracle."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ['output', 'manifest', 'products', 'source', 'prefix']:
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    base = args.output.resolve(); base.mkdir(exist_ok=False)
    products = args.products.resolve(); runs = []
    checker = ROOT / 'tests/check_plasmaag_native.py'
    files = [p for p in products.rglob('*') if p.is_file()]
    initial = {str(p.relative_to(products)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    for phase in ['positive', 'foreign-dna', 'missing-membership', 'invalid-score']:
        folder = base / phase; folder.mkdir()
        view = folder / 'results'; view.mkdir()
        for original in files:
            target = view / original.relative_to(products); target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(original)
        if phase == 'foreign-dna':
            target = next((view / 'candidate_plasmids').glob('*.fna'))
            lines = target.read_text().splitlines(keepends=True)
            index = next(i for i, line in enumerate(lines) if line.strip() and not line.startswith('>'))
            lines[index] = ('T' if lines[index][0].upper() != 'T' else 'A') + lines[index][1:]
            target.unlink(); target.write_text(''.join(lines))
        elif phase == 'missing-membership':
            target = view / 'candidate_plasmids.tsv'; lines = target.read_text().splitlines(keepends=True)
            assert len(lines) > 1; target.unlink(); target.write_text(''.join(lines[:-1]))
        elif phase == 'invalid-score':
            target = view / 'plasmid_scores.tsv'; lines = target.read_text().splitlines(keepends=True)
            assert len(lines) > 1; cells = lines[1].strip().split('\t'); cells[1] = 'nan'; lines[1] = '\t'.join(cells) + '\n'
            target.unlink(); target.write_text(''.join(lines))
        cmd = [sys.executable, str(checker), '--manifest', str(args.manifest.resolve()), '--products', str(view), '--output', str(folder / 'check.json')]
        result = subprocess.run(cmd, text=True, capture_output=True)
        (folder / 'stdout').write_text(result.stdout); (folder / 'stderr').write_text(result.stderr)
        passed = result.returncode == 0 if phase == 'positive' else result.returncode != 0 and 'AssertionError' in result.stderr
        runs.append(dict(phase=phase, command=cmd, exit_code=result.returncode, expected_outcome=passed))
        assert passed, runs[-1]
    source = base / 'private-source'
    shutil.copytree(args.source.resolve(), source, ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc'))
    modified = source / 'PlasMAAG/__main__.py'; data = modified.read_bytes(); stamp = modified.stat()
    corrupt = data.replace(b'import', b'IMPORT', 1); assert data != corrupt and len(data) == len(corrupt)
    modified.write_bytes(corrupt)
    import os
    os.utime(modified, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    folder = base / 'foreign-source'; folder.mkdir()
    cmd = [str(args.prefix.resolve() / 'bin/python'), str(ROOT / 'bin/plasmaag_checked.py'), '--source', str(source), '--runtime-record', str(folder / 'runtime.json'), '--', '--help']
    result = subprocess.run(cmd, text=True, capture_output=True)
    (folder / 'stdout').write_text(result.stdout); (folder / 'stderr').write_text(result.stderr)
    record = json.loads((folder / 'runtime.json').read_text())
    assert result.returncode != 0 and record['children'] == [] and 'Unsupported PlasMAAG source: PlasMAAG/__main__.py' in record['error']
    runs.append(dict(phase='foreign-source', command=cmd, exit_code=result.returncode, expected_outcome=True,
                     changed_sha256=hashlib.sha256(corrupt).hexdigest(), original_sha256=hashlib.sha256(data).hexdigest(),
                     bytes=len(data), preserved_mtime_ns=stamp.st_mtime_ns))
    unchanged = initial == {str(p.relative_to(products)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    assert unchanged
    (base / 'run.json').write_text(json.dumps(dict(pass_=True, original_products_unchanged=unchanged, runs=runs,
        scope='Actual complete native outputs pass; private DNA/membership/score corruption rejected; fixed source mutation rejected before CLI/children. No biological accuracy claim'), indent=2).replace('"pass_":', '"pass":') + '\n')


if __name__ == '__main__':
    main()
