#!/usr/bin/env python3
"""Internal effect-size differential plasmid abundance between groups.

Standalone implementation of the ABI ``internal_effect_size`` method for the
``multisample_differential_abundance`` node. For every pair of groups with at
least ``--min-replicates`` samples it computes, per contig:

* log2 fold change of mean coverage (pseudocount 1e-6),
* Welch's t statistic with a normal-approximation p-value,
* Benjamini-Hochberg adjusted p-values,
* Hedges' g effect size.

Output schema follows the ABI ``differential_abundance`` standard table.
"""

import argparse
import csv
import math
from collections import defaultdict
from itertools import combinations

PSEUDOCOUNT = 1e-6


def normal_sf(x):
    """Two-sided p-value for a standard normal statistic (|x|)."""
    return math.erfc(abs(x) / math.sqrt(2.0))


def load_abundance(path):
    values = defaultdict(dict)
    with open(path) as fh:
        for rec in csv.DictReader(fh, delimiter="\t"):
            try:
                cov = float(rec.get("coverage") or 0)
            except ValueError:
                cov = 0.0
            values[rec["sample_id"]][rec["contig_id"]] = cov
    return values


def load_groups(path):
    groups = defaultdict(list)
    with open(path) as fh:
        for rec in csv.DictReader(fh, delimiter="\t"):
            sid, grp = rec.get("sample_id", ""), rec.get("group", "")
            if sid and grp:
                groups[grp].append(sid)
    return groups


def welch(a, b):
    na, nb = len(a), len(b)
    ma = sum(a) / na
    mb = sum(b) / nb
    va = sum((x - ma) ** 2 for x in a) / (na - 1) if na > 1 else 0.0
    vb = sum((x - mb) ** 2 for x in b) / (nb - 1) if nb > 1 else 0.0
    se = math.sqrt(va / na + vb / nb)
    if se == 0:
        return None
    return (ma - mb) / se


def hedges_g(a, b):
    na, nb = len(a), len(b)
    ma = sum(a) / na
    mb = sum(b) / nb
    va = sum((x - ma) ** 2 for x in a) / (na - 1) if na > 1 else 0.0
    vb = sum((x - mb) ** 2 for x in b) / (nb - 1) if nb > 1 else 0.0
    pooled = math.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2)) if na + nb > 2 else 0.0
    if pooled == 0:
        return 0.0
    d = (ma - mb) / pooled
    correction = 1 - 3 / (4 * (na + nb) - 9) if na + nb > 2 else 1.0
    return d * correction


def bh_adjust(pvals):
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [1.0] * m
    prev = 1.0
    for rank, i in enumerate(reversed(order), start=1):
        k = m - rank + 1
        prev = min(prev, pvals[i] * m / k)
        adj[i] = min(prev, 1.0)
    return adj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--abundance", required=True)
    ap.add_argument("--metadata", required=True)
    ap.add_argument("--min-replicates", type=int, default=3)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    values = load_abundance(args.abundance)
    groups = load_groups(args.metadata)
    eligible = {g: s for g, s in groups.items()
                if len([x for x in s if x in values]) >= args.min_replicates}
    contigs = sorted({c for s in values.values() for c in s})

    rows = []
    pvals = []
    for g1, g2 in combinations(sorted(eligible), 2):
        s1 = [s for s in eligible[g1] if s in values]
        s2 = [s for s in eligible[g2] if s in values]
        for cid in contigs:
            a = [values[s].get(cid, 0.0) for s in s1]
            b = [values[s].get(cid, 0.0) for s in s2]
            ma = sum(a) / len(a)
            mb = sum(b) / len(b)
            log2fc = math.log2((ma + PSEUDOCOUNT) / (mb + PSEUDOCOUNT))
            t = welch(a, b)
            p = normal_sf(t) if t is not None else 1.0
            g = hedges_g(a, b)
            rows.append({"contig_id": cid, "group1": g1, "group2": g2,
                         "log2fc": f"{log2fc:.6f}", "pvalue": f"{p:.6g}",
                         "effect_size": f"{g:.6f}", "method": "internal_effect_size"})
            pvals.append(p)

    adj = bh_adjust(pvals) if pvals else []
    for row, q in zip(rows, adj):
        row["padj"] = f"{q:.6g}"

    with open(args.out, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["contig_id", "group1", "group2", "log2fc",
                                                "pvalue", "padj", "effect_size", "method"],
                                delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    print(f"differential abundance: {len(rows)} test(s), {len(eligible)} eligible group(s)")


if __name__ == "__main__":
    main()
