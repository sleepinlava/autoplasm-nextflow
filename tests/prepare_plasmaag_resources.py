#!/usr/bin/env python3
"""Prepare the exact full PlasMAAG workflow source; the environment supplies its compiled package."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); lock = json.loads((ROOT / 'tests/plasmaag-native.lock.json').read_text())
    platform_pin = ROOT / 'envs/plasmaag-genomad.linux-64.pin.txt'
    pin_text = platform_pin.read_text()
    pins = [line for line in pin_text.splitlines() if line and not line.startswith('#') and line != '@EXPLICIT']
    if '@EXPLICIT' not in pin_text.splitlines() or len(pins) != 163 or not all(
            re.fullmatch(r'https://conda\.anaconda\.org/(?:conda-forge|bioconda)/(?:linux-64|noarch)/[^/\s#]+#[a-f0-9]{64}', line) for line in pins):
        raise ValueError('Expected reviewed remote geNomad platform pin with163 SHA256 archives')
    if hashlib.sha256(args.archive.read_bytes()).hexdigest() != lock['archive_sha256']:
        raise ValueError('PlasMAAG archive checksum differs from fixed source')
    if args.output.exists(): raise ValueError('Output already exists')
    with tempfile.TemporaryDirectory(dir=args.output.resolve().parent) as temp:
        temp = Path(temp)
        with tarfile.open(args.archive) as archive:
            archive.extractall(temp, filter='data')
        roots = [p for p in temp.iterdir() if p.is_dir()]; assert len(roots) == 1
        source = roots[0]
        for name, expected in lock['source_sha256'].items():
            p = source / name
            if p.is_symlink() or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != expected:
                raise ValueError('Fixed PlasMAAG source mismatch: ' + name)
        shutil.copytree(source, args.output)
    (args.output / 'envs/genomad.linux-64.pin.txt').write_bytes(platform_pin.read_bytes())
    (args.output / 'resource_provenance.json').write_text(json.dumps(dict(commit=lock['commit'], archive_sha256=lock['archive_sha256'],
        source_sha256=lock['source_sha256'], deployment_supplements={'envs/genomad.linux-64.pin.txt': hashlib.sha256(platform_pin.read_bytes()).hexdigest()},
        architecture='linux-64; this resolved lock includes x86_64_v4 packages, check target CPU before deployment',
        scope='Complete immutable workflow source plus remote platform deployment pin; compiled package is verified in the execution environment'), indent=2) + '\n')


if __name__ == '__main__': main()
