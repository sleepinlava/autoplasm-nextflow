#!/usr/bin/env python3
"""Prepare a sample-aware FASTA input for cross-sample plasmid clustering.

Accepted input basenames are ``<sample>.plasmid_contigs.fasta``, the legacy
``<sample>__plasmid_contigs.fasta``, and ``plasmid_contigs.fasta`` inside a
sample-named directory. Every output identifier is ``sample|contig``.
"""

import argparse
import os
import tempfile
from pathlib import Path


def infer_sample_id(path):
    """Return the sample ID encoded by one supported consensus FASTA name."""
    path = Path(path)
    name = path.name
    if name.endswith(".plasmid_contigs.fasta"):
        sample = name[:-len(".plasmid_contigs.fasta")]
    elif name.endswith("__plasmid_contigs.fasta"):
        sample = name[:-len("__plasmid_contigs.fasta")]
    elif name == "plasmid_contigs.fasta":
        sample = path.parent.name
    else:
        raise ValueError(f"Unsupported plasmid FASTA naming: {path}")
    if not sample:
        raise ValueError(f"Invalid sample ID in {path}: sample ID is empty")
    if any(char.isspace() for char in sample):
        raise ValueError(f"Invalid sample ID in {path}: whitespace is not allowed")
    if "|" in sample:
        raise ValueError(f"Invalid sample ID in {path}: '|' is not allowed")
    return sample


def read_fasta(path):
    """Yield FASTA (identifier, sequence) pairs, rejecting malformed headers."""
    try:
        with open(path, encoding="utf-8") as fh:
            name, seq = None, []
            for line_number, line in enumerate(fh, 1):
                line = line.rstrip("\r\n")
                if line.startswith(">"):
                    if name is not None:
                        yield name, "".join(seq)
                    header = line[1:].strip()
                    if not header:
                        raise ValueError(f"{path}:{line_number}: empty FASTA header")
                    name, seq = header.split()[0], []
                elif line.strip():
                    if name is None:
                        raise ValueError(f"{path}:{line_number}: sequence data before FASTA header")
                    seq.append(line.strip())
            if name is not None:
                yield name, "".join(seq)
    except OSError as exc:
        raise ValueError(f"Cannot read FASTA {path}: {exc}") from exc


def write_catalog(paths, target):
    """Write a validated catalog atomically without retaining sequences in RAM."""
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    seen_headers = {}
    n_records = 0
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            for path in sorted(map(Path, paths), key=lambda p: str(p)):
                sample = infer_sample_id(path)
                for cid, seq in read_fasta(path):
                    header = f"{sample}|{cid}"
                    if header in seen_headers:
                        raise ValueError(
                            f"Duplicate FASTA identifier {header!r} in {path}; "
                            f"first seen in {seen_headers[header]}"
                        )
                    seen_headers[header] = path
                    out.write(f">{header}\n")
                    for i in range(0, len(seq), 80):
                        out.write(seq[i:i + 80] + "\n")
                    n_records += 1
        os.replace(temporary, target)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return n_records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contigs", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    try:
        n_records = write_catalog(args.contigs, args.out)
    except (OSError, ValueError) as exc:
        ap.error(str(exc))
    print(f"catalog prepared from {len(args.contigs)} file(s), {n_records} record(s)")


if __name__ == "__main__":
    main()
