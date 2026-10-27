#!/usr/bin/env python3
"""Pilot for default SemiBin's bundled marker resource, inside its runtime.

This deliberately does not certify custom flags, pretrained models, GTDB,
containers, or the production workflow's runtime selection.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import stat


def capture():
    version = importlib.import_module('SemiBin.semibin_version')
    if version.__version__ != '2.4.1':
        raise ValueError('Pilot requires native SemiBin 2.4.1')
    marker = Path(version.__file__).parent / 'marker.hmm'
    before = marker.stat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError('SemiBin marker must be a readable regular file')
    digest = hashlib.sha256(marker.read_bytes()).hexdigest()
    after = marker.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError('SemiBin marker changed while hashing')
    return dict(schema_version=1, scope='semibin_2.4.1_default_marker_pilot',
                version=version.__version__,
                resource=dict(name='marker.hmm', bytes=after.st_size,
                              sha256=digest, mode=stat.S_IMODE(after.st_mode)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    identity = capture()
    if args.verify is not None:
        if json.loads(args.verify.read_text()) != identity:
            raise ValueError('Runtime marker differs from pre-lookup identity')
    if args.output is not None:
        args.output.write_text(json.dumps(identity, sort_keys=True, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    main()
