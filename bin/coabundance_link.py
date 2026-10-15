#!/usr/bin/env python3
"""Correlate plasmid coverage with species-level MetaPhlAn profiles."""

import argparse
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path


def load_plasmid_abundance(path):
    plasmids = defaultdict(dict)
    try:
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh, delimiter="\t")
            if not reader.fieldnames:
                raise ValueError(f"{path}: missing TSV header")
            fields = {name.strip(): name for name in reader.fieldnames}
            id_col = fields.get("plasmid_id") or fields.get("contig_id")
            sample_col = fields.get("sample_id")
            coverage_col = fields.get("coverage")
            missing = [name for name, col in (("plasmid_id/contig_id", id_col),
                                               ("sample_id", sample_col),
                                               ("coverage", coverage_col)) if col is None]
            if missing:
                raise ValueError(
                    f"{path}: expected merged abundance TSV columns; missing {', '.join(missing)}"
                )
            seen = {}
            for line_number, rec in enumerate(reader, 2):
                cid = (rec.get(id_col) or "").strip()
                sample = (rec.get(sample_col) or "").strip()
                if not cid or not sample:
                    raise ValueError(f"{path}:{line_number}: empty plasmid ID or sample_id")
                try:
                    cov = float(rec.get(coverage_col) or "")
                except ValueError as exc:
                    raise ValueError(f"{path}:{line_number}: invalid coverage value") from exc
                if not math.isfinite(cov) or cov < 0:
                    raise ValueError(f"{path}:{line_number}: coverage must be finite and non-negative")
                key = (cid, sample)
                if key in seen:
                    raise ValueError(
                        f"{path}:{line_number}: duplicate ({sample!r}, {cid!r}); "
                        f"first seen on line {seen[key]}"
                    )
                seen[key] = line_number
                plasmids[cid][sample] = cov
    except OSError as exc:
        raise ValueError(f"Cannot read plasmid abundance TSV {path}: {exc}") from exc
    return plasmids


def inferred_profile_id(path):
    name = Path(path).name
    suffix = ".metaphlan.tsv"
    return name[:-len(suffix)] if name.endswith(suffix) else Path(name).stem


def load_host_profiles(paths, sample_ids):
    if len(paths) != len(sample_ids):
        raise ValueError(f"received {len(sample_ids)} host sample ID(s) for {len(paths)} profile(s)")
    if any(not sample.strip() for sample in sample_ids):
        raise ValueError("host profile sample IDs must not be empty")
    if len(set(sample_ids)) != len(sample_ids):
        raise ValueError("duplicate host profile sample IDs")

    taxa = defaultdict(dict)
    valid_samples = set()
    for path, sample in zip(paths, sample_ids):
        header = None
        try:
            with open(path, newline="", encoding="utf-8") as fh:
                reader = csv.reader(fh, delimiter="\t")
                for line_number, row in enumerate(reader, 1):
                    if not row or not any(cell.strip() for cell in row):
                        continue
                    first = row[0].strip()
                    normalized = [cell.strip() for cell in row]
                    normalized[0] = normalized[0].lstrip("#").strip()
                    if "clade_name" in normalized and "relative_abundance" in normalized:
                        header = normalized
                        clade_index = header.index("clade_name")
                        abundance_index = header.index("relative_abundance")
                        continue
                    if first.startswith("#"):
                        continue
                    if header is None:
                        raise ValueError(
                            f"{path}:{line_number}: missing clade_name/relative_abundance header"
                        )
                    if len(row) <= max(clade_index, abundance_index):
                        raise ValueError(f"{path}:{line_number}: row has fewer columns than its header")
                    clade = row[clade_index].strip()
                    terminal = clade.split("|")[-1]
                    if not terminal.startswith("s__") or terminal == "s__":
                        continue
                    try:
                        abundance = float(row[abundance_index].strip())
                    except ValueError as exc:
                        raise ValueError(f"{path}:{line_number}: invalid relative_abundance") from exc
                    if not math.isfinite(abundance) or abundance < 0:
                        raise ValueError(
                            f"{path}:{line_number}: relative_abundance must be finite and non-negative"
                        )
                    if clade in taxa and sample in taxa[clade]:
                        raise ValueError(
                            f"{path}:{line_number}: duplicate species row {clade!r} for sample {sample!r}"
                        )
                    taxa[clade][sample] = abundance
        except OSError as exc:
            raise ValueError(f"Cannot read MetaPhlAn profile {path}: {exc}") from exc
        if header is None:
            raise ValueError(f"{path}: missing clade_name/relative_abundance header")
        valid_samples.add(sample)
    return valid_samples, taxa


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


def run(args):
    plasmids = load_plasmid_abundance(args.plasmid_abundance)
    if args.host_sample_ids is None:
        sample_ids = [inferred_profile_id(path) for path in args.host_profiles]
    else:
        sample_ids = args.host_sample_ids
    profile_samples, taxa = load_host_profiles(args.host_profiles, sample_ids)
    plasmid_samples = {sample for profile in plasmids.values() for sample in profile}
    samples = sorted(plasmid_samples & profile_samples)

    rows = []
    if len(samples) >= 3:
        for cid, profile in sorted(plasmids.items()):
            pv = [profile.get(sample, 0.0) for sample in samples]
            if args.method == "spearman":
                pv = rank(pv)
            for taxon, tprofile in sorted(taxa.items()):
                tv = [tprofile.get(sample, 0.0) for sample in samples]
                if args.method == "spearman":
                    tv = rank(tv)
                correlation = pearson(pv, tv)
                if abs(correlation) >= args.min_correlation:
                    rows.append([cid, taxon, ",".join(samples), "co_abundance",
                                 f"{correlation:.4f}",
                                 f"method={args.method};n_samples={len(samples)}"])

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(["plasmid_id", "host_id", "sample_id", "evidence_type", "score", "supporting_data"])
        writer.writerows(rows)
    print(
        f"plasmid samples: {len(plasmid_samples)}; valid host profiles: {len(profile_samples)}; "
        f"shared samples: {len(samples)}; links: {len(rows)}",
        file=sys.stderr,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plasmid-abundance", required=True)
    ap.add_argument("--host-profiles", nargs="*", required=True, type=Path)
    ap.add_argument("--host-sample-ids", nargs="*", default=None,
                    help="Sample IDs paired by position with the MetaPhlAn profiles")
    ap.add_argument("--method", default="spearman", choices=["spearman", "pearson"])
    ap.add_argument("--min-correlation", type=float, default=0.6)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    try:
        run(args)
    except (OSError, ValueError, csv.Error) as exc:
        ap.error(str(exc))


if __name__ == "__main__":
    main()
