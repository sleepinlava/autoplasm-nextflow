#!/usr/bin/env python3
"""Run reviewed CONCOCT1.1.0 cut helper with correct overlapping BED stride.

The original source/CLI/sequence slicing stays unchanged. Only the BED
coordinate expression is corrected to the actual chunk_size-overlap stride.
Refuse an unreviewed executable rather than patching another implementation.
"""
import hashlib
from pathlib import Path
import shutil
import sys

SOURCE_BLOB = 'c4e7f4dbff1ca0ff763ac9d7feda28e8c10c11c3'
ORIGINAL = 'chunk_size*i, chunk_size*i+len(split_seq)'
CORRECTED = '(chunk_size-overlap)*i, (chunk_size-overlap)*i+len(split_seq)'


def checked_source(path):
    data = Path(path).read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    if blob != SOURCE_BLOB:
        raise ValueError('CONCOCT cut helper source differs from reviewed1.1.0: ' + blob)
    source = data.decode('utf-8')
    if source.count(ORIGINAL) != 1:
        raise ValueError('Reviewed CONCOCT BED coordinate expression is not unique')
    return source.replace(ORIGINAL, CORRECTED)


def main():
    executable = shutil.which('cut_up_fasta.py')
    if executable is None:
        raise ValueError('cut_up_fasta.py is not on PATH')
    source = checked_source(executable)
    sys.argv[0] = executable
    exec(compile(source, executable, 'exec'), {'__name__': '__main__', '__file__': executable})


if __name__ == '__main__':
    try:
        main()
    except ValueError as error:
        raise SystemExit('CONCOCT cut interface: ' + str(error))
