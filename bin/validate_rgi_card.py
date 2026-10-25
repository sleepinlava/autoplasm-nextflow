#!/usr/bin/env python3
"""Identify a prepared CARD by its JSON version and verify RGI's task-local copy."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


def read_json(path):
    with path.open() as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError('Expected JSON object: {}'.format(path))
    return data


def validate(card, loaded=None):
    source = card / 'card.json'
    data = read_json(source)
    version = data.get('_version')
    if not isinstance(version, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', version):
        raise ValueError('Invalid CARD JSON version in {}'.format(source))
    if not any(k.isdigit() and isinstance(v, dict) for k, v in data.items()):
        raise ValueError('CARD JSON has no model records: {}'.format(source))
    for suffix in ['', '_all']:
        path = card / ('card_database_v' + version + suffix + '.fasta')
        if not path.is_file():
            raise ValueError('Missing CARD annotation file for JSON version {}: {}'.format(version, path))
    if loaded is not None:
        copied = loaded / 'card.json'
        if hashlib.sha256(copied.read_bytes()).digest() != hashlib.sha256(source.read_bytes()).digest():
            raise ValueError('Loaded CARD JSON differs from declared input: {}'.format(copied))
        metadata = read_json(loaded / 'loaded_databases.json')
        record = metadata.get('card_json')
        if not isinstance(record, dict) or record.get('data_version') != version:
            raise ValueError('Loaded CARD version metadata differs from declared input: {}'.format(loaded))
    return version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--card', type=Path, required=True)
    parser.add_argument('--loaded', type=Path)
    args = parser.parse_args()
    try:
        print(validate(args.card, args.loaded))
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
