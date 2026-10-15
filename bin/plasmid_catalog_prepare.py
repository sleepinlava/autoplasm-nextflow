#!/usr/bin/env python3
"""Prepare the cross-sample non-redundant plasmid catalog input.

Standalone implementation of the ABI internal handler
``metagenomic_plasmid.plasmid_catalog_prepare``: concatenates every per-sample
plasmid_contigs.fasta into one FASTA. Headers are prefixed with the sample id
(derived from the staged file name ``<sample>__plasmid_contigs.fasta``) so
cluster members stay traceable to their sample.
"""

import argparse
from pathlib import Path


def read_fasta(path):
    name, seq = None, []
    with open(path) as fh:
        for line in fh:
            line = line.rstrip()
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(seq)
                name, seq = line[1:].split()[0], []
            elif name is not None:
                seq.append(line.strip())
    if name is not None:
        yield name, "".join(seq)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contigs", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    n_records = 0
    with open(args.out, "w") as out:
        for path in sorted(args.contigs):
            p = Path(path)
            name = p.name
            # sample id: '<sample>__file' staging convention, else parent dir
            sample = name.split("__")[0] if "__" in name else p.parent.name
            for cid, seq in read_fasta(p):
                out.write(f">{sample}|{cid}\n")
                for i in range(0, len(seq), 80):
                    out.write(seq[i:i + 80] + "\n")
                n_records += 1
    print(f"catalog prepared from {len(args.contigs)} file(s), {n_records} record(s)")


if __name__ == "__main__":
    main()
