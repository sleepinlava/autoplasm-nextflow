#!/usr/bin/env python3
"""Make GTDB-Tk's directory input homogeneous without changing genome IDs.

Final MAG producers emit plain or gzip fa/fna/fasta files. GTDB-Tk selects
one extension and derives genome IDs from those names. Decode into private
*.fna files, preserving the original FASTA bytes and suffix-independent ID.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import zlib

SUFFIX = re.compile(r'\.(?:fa|fna|fasta)(?:\.gz)?$', re.IGNORECASE)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def normalize(source, destination, manifest):
    source, destination, manifest = map(Path, [source, destination, manifest])
    if not source.is_dir():
        raise ValueError('GTDB-Tk input must be a directory of bin FASTA files')
    if destination.resolve().is_relative_to(source.resolve()):
        raise ValueError('Normalized GTDB-Tk directory must be outside input')
    if any(manifest.resolve().is_relative_to(p.resolve()) for p in [source, destination]):
        raise ValueError('GTDB-Tk manifest must be outside input and normalized directories')
    prepared = []; seen = set()
    for path in sorted(source.iterdir(), key=lambda p: p.name):
        if not path.is_file():
            raise ValueError(f'GTDB-Tk bin input is not a file: {path.name}')
        match = SUFFIX.search(path.name)
        if not match:
            raise ValueError(f'Unsupported GTDB-Tk bin FASTA suffix: {path.name}')
        genome_id = path.name[:match.start()]
        if not genome_id or any(c in genome_id for c in '()[],;= \t\r\n'):
            raise ValueError(f'Invalid GTDB-Tk genome ID: {genome_id!r}')
        if genome_id in seen:
            raise ValueError(f'Duplicate GTDB-Tk genome ID after suffix removal: {genome_id}')
        seen.add(genome_id)
        original = path.read_bytes()
        compressed = original.startswith(b'\x1f\x8b')
        if path.name.lower().endswith('.gz') and not compressed:
            raise ValueError(f'Invalid gzip GTDB-Tk bin: {path.name}')
        decoded = gzip.decompress(original) if compressed else original
        if not decoded.strip() or not decoded.lstrip().startswith(b'>'):
            raise ValueError(f'Empty or non-FASTA GTDB-Tk bin: {path.name}')
        prepared.append((genome_id + '.fna', decoded, {
            'input_name': path.name, 'genome_id': genome_id,
            'normalized_name': genome_id + '.fna', 'gzip_decoded': compressed,
            'input_sha256': sha(original), 'fasta_sha256': sha(decoded),
            'input_bytes': len(original), 'fasta_bytes': len(decoded)}))
    if not prepared:
        raise ValueError('GTDB-Tk bin directory is empty; no-genome samples must not invoke classification')
    # Validate every input before writing any result. A retry may reuse exactly
    # these files; changed/stale contents must not silently join the analysis.
    if destination.exists():
        if not destination.is_dir() or {p.name for p in destination.iterdir()} != {p[0] for p in prepared}:
            raise ValueError('Existing GTDB-Tk normalized directory has unexpected contents')
        for name, data, record in prepared:
            target = destination / name
            if not target.is_file() or target.is_symlink() or target.read_bytes() != data:
                raise ValueError(f'Existing GTDB-Tk normalized file differs: {name}')
    else:
        destination.mkdir(parents=True)
        for name, data, record in prepared:
            (destination / name).write_bytes(data)
    result = {'status': 'normalized', 'extension': 'fna', 'genomes': len(prepared),
        'identity': 'FASTA suffix removed case-insensitively; original genome stem and FASTA bytes retained',
        'files': [record for _, _, record in prepared]}
    manifest.write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    args = parser.parse_args()
    try:
        normalize(args.input_dir, args.output_dir, args.manifest)
    except (ValueError, OSError, EOFError, zlib.error) as error:
        print(f'normalize_gtdb_bins: {error}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
