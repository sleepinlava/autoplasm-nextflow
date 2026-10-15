#!/usr/bin/env python3
"""Prepare the compositional abundance matrix for FastSpar.

Converts the merged plasmid abundance table into FastSpar's OTU-table layout
(rows = contigs, columns = samples, first header cell ``#OTU ID``). CoverM
does not emit raw counts, so rounded coverage is used as the count proxy
(same convention as the ABI DESeq2 script).
"""

import argparse
import csv
from collections import defaultdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--abundance", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    matrix = defaultdict(dict)
    samples = set()
    with open(args.abundance) as fh:
        for rec in csv.DictReader(fh, delimiter="\t"):
            cid = rec.get("contig_id") or rec.get("plasmid_id") or ""
            value = rec.get("raw_count") or rec.get("coverage") or "0"
            try:
                v = max(0, round(float(value)))
            except ValueError:
                v = 0
            matrix[cid][rec["sample_id"]] = v
            samples.add(rec["sample_id"])

    samples = sorted(samples)
    with open(args.out, "w", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(["#OTU ID"] + samples)
        for cid in sorted(matrix):
            writer.writerow([cid] + [matrix[cid].get(s, 0) for s in samples])
    print(f"fastspar input: {len(matrix)} contig(s) x {len(samples)} sample(s)")


if __name__ == "__main__":
    main()
