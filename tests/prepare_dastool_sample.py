#!/usr/bin/env python3
"""Verify a local copy of the locked DAS Tool official sample; no downloads.

Acquire files from the URLs in dastool-sample.lock.json into one directory,
then run this checker before run_dastool_export.py. It refuses replacements
and validates the independent upstream expected products as well as inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path


def verify(directory):
    lock = json.loads(Path(__file__).with_name('dastool-sample.lock.json').read_text())
    for record in lock['files']:
        path = directory / record['name']
        data = path.read_bytes()
        if len(data) != record['size'] or hashlib.sha256(data).hexdigest() != record['sha256']:
            raise ValueError('Locked sample checksum mismatch: ' + str(path))
        if hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() != record['git_blob']:
            raise ValueError('Upstream Git blob mismatch: ' + str(path))
    return len(lock['files'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    print('Verified', verify(args.directory), 'fixed official sample files')
