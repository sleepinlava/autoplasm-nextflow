#!/usr/bin/env python3
"""Alpha/beta diversity analysis over the merged contig abundance table.

Alpha: richness (contigs with coverage > 0) and Shannon index per sample.
Beta: pairwise Bray-Curtis dissimilarity on coverage values.

Output schemas follow the ABI ``sample_diversity`` standard table.
Stdlib + csv only.
"""

import argparse
import csv
import math
from collections import defaultdict


def load_abundance(path):
    values = defaultdict(dict)  # sample -> {contig: coverage}
    with open(path) as fh:
        for rec in csv.DictReader(fh, delimiter="\t"):
            try:
                cov = float(rec.get("coverage") or 0)
            except ValueError:
                cov = 0.0
            values[rec["sample_id"]][rec["contig_id"]] = cov
    return values


def load_metadata(path):
    groups = {}
    with open(path) as fh:
        for rec in csv.DictReader(fh, delimiter="\t"):
            groups[rec.get("sample_id", "")] = rec.get("group", "")
    return groups


def shannon(counts):
    total = sum(counts)
    if total <= 0:
        return 0.0
    return -sum((c / total) * math.log(c / total) for c in counts if c > 0)


def bray_curtis(a, b, contigs):
    num = sum(abs(a.get(c, 0.0) - b.get(c, 0.0)) for c in contigs)
    den = sum(a.get(c, 0.0) + b.get(c, 0.0) for c in contigs)
    return num / den if den > 0 else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--abundance", required=True)
    ap.add_argument("--metadata", required=True)
    ap.add_argument("--out-metrics", required=True)
    ap.add_argument("--out-beta", required=True)
    args = ap.parse_args()

    values = load_abundance(args.abundance)
    groups = load_metadata(args.metadata)
    samples = sorted(values)
    contigs = sorted({c for s in values.values() for c in s})

    with open(args.out_metrics, "w", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(["sample_id", "metric", "value", "group"])
        for s in samples:
            covs = [values[s].get(c, 0.0) for c in contigs]
            writer.writerow([s, "richness", sum(1 for c in covs if c > 0), groups.get(s, "")])
            writer.writerow([s, "shannon", f"{shannon(covs):.6f}", groups.get(s, "")])

    with open(args.out_beta, "w", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(["sample_id"] + samples)
        for s1 in samples:
            row = [s1] + [f"{bray_curtis(values[s1], values[s2], contigs):.6f}" for s2 in samples]
            writer.writerow(row)


if __name__ == "__main__":
    main()
