#!/usr/bin/env python3
"""Candidate validation of default Medaka2.2.2 adjacent reference indexes.

Rebuild with the fixed native mini_align -X in a private directory, and require
any reused index to equal that canonical result. This does not integrate the
production cache gate or cover RLE-transformed references or forced -x indexes.
Original references/indexes are never written. Missing indexes are recorded as
absent, not created alongside the source. A receipt is not scientific acceptance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile


MINI_ALIGN_SHA = '717ad91898f1e4f04fc7c221c2db5885b1274d77b32b57ff6f322852a03b4634'


def identity(path):
    path = Path(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError('Index/reference must be a regular file: ' + str(path))
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
            before.st_mode) != (after.st_dev, after.st_ino, after.st_size,
                              after.st_mtime_ns, after.st_mode):
        raise ValueError('Resource changed while hashing: ' + str(path))
    return {'resolved_path': str(path.resolve(strict=True)),
            'bytes': after.st_size, 'sha256': digest.hexdigest(),
            'mode': stat.S_IMODE(after.st_mode)}


def capture(assembly, threads=1):
    import medaka
    if medaka.__version__ != '2.2.2':
        raise ValueError('Index resolver requires native Medaka2.2.2')
    native = Path(sys.prefix) / 'bin/mini_align'
    native_identity = identity(native)
    if native_identity['sha256'] != MINI_ALIGN_SHA:
        raise ValueError('Fixed native mini_align source differs')
    source = Path(assembly).resolve(strict=True)
    before = identity(source)
    # Native consensus follows realpath before locating the adjacent indexes.
    suffixes = ['.fai', '.map-ont.mmi', '.gzi']
    adjacent = {}
    for suffix in suffixes:
        path = Path(str(source) + suffix)
        adjacent[suffix] = identity(path) if os.path.lexists(path) else None
    tools = {}
    for name in ['samtools', 'minimap2']:
        path = shutil.which(name)
        if path is None:
            raise ValueError('Native index tool missing: ' + name)
        tools[name] = identity(path)
    with tempfile.TemporaryDirectory(prefix='medaka-canonical-index-') as directory:
        draft = Path(directory) / source.name
        shutil.copyfile(source, draft)
        if identity(draft)['sha256'] != before['sha256']:
            raise ValueError('Reference changed while copying')
        command = [str(native), '-X', '-r', str(draft), '-t', str(threads)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=240)
        if result.returncode:
            raise ValueError('Native canonical index preparation failed: ' + result.stderr)
        canonical = {}
        for suffix in suffixes:
            path = Path(str(draft) + suffix)
            canonical[suffix] = identity(path) if path.exists() else None
            actual = adjacent[suffix]
            expected = canonical[suffix]
            if actual is not None and (expected is None or
                    actual['sha256'] != expected['sha256']):
                raise ValueError('Adjacent Medaka index differs from native reference rebuild: ' + suffix)
            if expected is not None:
                # Do not put the random private rebuild path in the cache identity.
                canonical[suffix] = {k: v for k, v in expected.items()
                                     if k != 'resolved_path'}
        if canonical['.fai'] is None or canonical['.map-ont.mmi'] is None:
            raise ValueError('Native index rebuild did not create FAI/MMI')
    if before != identity(source):
        raise ValueError('Reference changed during index validation')
    for suffix, original in adjacent.items():
        path = Path(str(source) + suffix)
        final = identity(path) if os.path.lexists(path) else None
        if final != original:
            raise ValueError('Adjacent index changed during validation: ' + suffix)
    if identity(native) != native_identity:
        raise ValueError('Native index program changed during validation')
    for name, original in tools.items():
        if identity(shutil.which(name)) != original:
            raise ValueError('Index tool changed during validation: ' + name)
    return {'schema': 1, 'scope': 'default non-RLE adjacent reference indexes only',
            'production_gate': False, 'formal_acceptance': False,
            'assembly': before, 'adjacent': adjacent,
            'canonical': canonical, 'native': native_identity, 'tools': tools}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assembly', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expect', type=Path)
    parser.add_argument('--threads', type=int, default=1)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output path')
    observed = capture(args.assembly, args.threads)
    if args.expect and json.loads(args.expect.read_text()) != observed:
        raise ValueError('Medaka adjacent index identity differs from expected receipt')
    with args.output.open('x') as stream:
        stream.write(json.dumps(observed, sort_keys=True, indent=2) + '\n')


if __name__ == '__main__':
    main()
