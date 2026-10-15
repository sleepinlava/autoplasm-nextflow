#!/usr/bin/env python3
"""Co-abundance correlation host-plasmid linking.

Correlates each plasmid contig's coverage profile across samples with each
host taxon's MetaPhlAn relative-abundance profile (spearman or pearson).
Reports links passing the correlation threshold. Stdlib only (Spearman via
rank transform, tie-averaged).

Output schema follows the ABI ``host_plasmid_links`` standard table.
"""

import argparse
import csv
import math
from collections import defaultdict


def load_plasmid_abundance(path):
    plasmids = defaultdict(dict)  # contig -> {sample: coverage}
    with open(path) as fh:
        for rec in csv.DictReader(fh, delimiter="\t"):
            cid = rec.get("contig_id") or rec.get("plasmid_id") or ""
            try:
                cov = float(rec.get("coverage") or 0)
            except ValueError:
                cov = 0.0
            plasmids[cid][rec["sample_id"]] = cov
    return plasmids


def load_host_profiles(paths):
    taxa = defaultdict(dict)  # taxon -> {sample: rel_abundance}
    for path in paths:
        sample = path.name.split("__")[0] if "__" in path.name else path.name.split(".")[0]
        with open(path) as fh:
            reader = csv.reader(fh, delimiter="\t")
            for row in reader:
                if not row or row[0].startswith("#"):
                    continue
                clade, abundance = row[0], row[-1]
                # species-level MetaPhlAn rows only
                if "s__" not in clade or "t__" in clade:
                    continue
                try:
                    taxa[clade][sample] = float(abundance)
                except ValueError:
                    continue
    return taxa


def rank(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        mean_rank = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = mean_rank
        i = j + 1
    return ranks


def pearson(x, y):
    n = len(x)
    mx = sum(x) / n
    my = sum(y) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y))
    vx = sum((a - mx) ** 2 for a in x)
    vy = sum((b - my) ** 2 for b in y)
    if vx == 0 or vy == 0:
        return 0.0
    return cov / math.sqrt(vx * vy)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plasmid-abundance", required=True)
    ap.add_argument("--host-profiles", nargs="+", required=True, type=lambda p: __import__("pathlib").Path(p))
    ap.add_argument("--method", default="spearman", choices=["spearman", "pearson"])
    ap.add_argument("--min-correlation", type=float, default=0.6)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    plasmids = load_plasmid_abundance(args.plasmid_abundance)
    taxa = load_host_profiles(args.host_profiles)
    samples = sorted({s for v in plasmids.values() for s in v} &
                     {s for v in taxa.values() for s in v})

    rows = []
    if len(samples) >= 3:
        for cid, profile in sorted(plasmids.items()):
            pv = [profile.get(s, 0.0) for s in samples]
            if args.method == "spearman":
                pv = rank(pv)
            for taxon, tprofile in sorted(taxa.items()):
                tv = [tprofile.get(s, 0.0) for s in samples]
                if args.method == "spearman":
                    tv = rank(tv)
                r = pearson(pv, tv)
                if abs(r) >= args.min_correlation:
                    rows.append([cid, taxon, ",".join(samples), "co_abundance",
                                 f"{r:.4f}", f"method={args.method};n_samples={len(samples)}"])

    with open(args.out, "w", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(["plasmid_id", "host_id", "sample_id", "evidence_type", "score", "supporting_data"])
        writer.writerows(rows)
    print(f"coabundance links: {len(rows)} link(s) across {len(samples)} shared sample(s)")


if __name__ == "__main__":
    main()
