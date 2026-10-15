#!/usr/bin/env python3
"""Detect plasmid circularity and terminal overlap.

Standalone port of the ABI internal handler
``metagenomic_plasmid.plasmid_structure`` (same algorithm: header-declared
circularity markers + exact prefix/suffix overlap, minimum 20 bp, maximum
1000 bp search window).
"""

import argparse
import csv


def read_fasta(path):
    name, seq = None, []
    with open(path) as fh:
        for line in fh:
            line = line.rstrip()
            if line.startswith(">"):
                if name is not None:
                    yield name, line_header, "".join(seq)
                line_header = line[1:].strip()
                name = line_header.split()[0] if line_header else ""
                seq = []
            elif name is not None:
                seq.append(line.strip())
    if name is not None:
        yield name, line_header, "".join(seq)


def terminal_overlap_length(sequence, minimum=20, maximum=1000):
    """Longest exact prefix/suffix overlap within conservative bounds."""
    upper = min(maximum, len(sequence) // 2)
    for size in range(upper, minimum - 1, -1):
        if sequence[:size] == sequence[-size:]:
            return size
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contigs", required=True)
    ap.add_argument("--sample-id", default="")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.out, "w", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(["sample_id", "plasmid_id", "length_bp", "is_circular",
                         "terminal_overlap_bp", "method", "warnings", "source_file"])
        n = 0
        for cid, header, seq in read_fasta(args.contigs):
            seq = seq.upper()
            overlap = terminal_overlap_length(seq)
            header_circular = any(m in header.lower() for m in
                                  ("circular=true", "topology=circular", "_circular"))
            writer.writerow([
                args.sample_id, cid, len(seq),
                str(bool(header_circular or overlap >= 20)).lower(),
                overlap, "header_or_exact_terminal_overlap",
                ("Sequence-based circularity is predictive and should be confirmed from "
                 "the assembly graph or read support."),
                args.contigs,
            ])
            n += 1
    print(f"plasmid structure: {n} sequence(s) evaluated")


if __name__ == "__main__":
    main()
