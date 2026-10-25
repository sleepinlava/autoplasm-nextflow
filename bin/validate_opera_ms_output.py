#!/usr/bin/env python3
"""Reject OPERA-MS results with fatal internal subprocess diagnostics.

OPERA-MS0.8.3 can return0 after a child process aborts. The final FASTA alone
does not establish successful coverage calculation or gap filling.
"""
import argparse
from pathlib import Path
import re
import sys

FATAL = re.compile(r'Assertion\s+.+\s+failed[.!]?|\bSegmentation fault\b|\bAborted\s*(?:\(core dumped\))?|'
                   r'error while loading shared libraries:|Can.t exec\s+|:\s*command not found\b', re.I)
REQUIRED = Path('intermediate_files/coverage_estimation/short_read_analysis.err')


def validate(directory):
    directory = Path(directory)
    required = directory/REQUIRED
    if not required.is_file() or required.is_symlink():
        raise ValueError(f'OPERA-MS coverage diagnostic missing or not a regular file: {REQUIRED}')
    checked = 0
    for path in sorted(directory.rglob('*')):
        if not (path.name.endswith(('.err','.log','.stderr')) or path.name == 'log.txt'):
            continue
        if path.is_symlink():
            raise ValueError(f'OPERA-MS diagnostic is a symlink: {path.relative_to(directory)}')
        if not path.is_file():
            continue
        with path.open(encoding='utf-8',errors='replace') as stream:
            for line_number,line in enumerate(stream,1):
                if FATAL.search(line):
                    raise ValueError(f'OPERA-MS internal process failure in {path.relative_to(directory)}:{line_number}: {line.strip()}')
        checked += 1
    return checked


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',required=True,type=Path)
    args=parser.parse_args()
    try:
        checked=validate(args.output_dir)
    except (ValueError,OSError) as error:
        print(str(error),file=sys.stderr)
        return 1
    print(f'Checked {checked} OPERA-MS diagnostic files; no recognized fatal subprocess diagnostic')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
