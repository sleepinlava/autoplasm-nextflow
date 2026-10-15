#!/usr/bin/env python3
"""Merge per-sample CoverM tables into a long-format abundance table.

Production workflows pass ``--sample-ids`` alongside the corresponding table
paths. Filename inference remains for older standalone CLI callers, but it is
ambiguous for IDs containing dots or suffix-like text.
"""

import argparse
import csv
import os
import sys
import tempfile
from pathlib import Path


def sample_from_name(path):
    """Legacy filename fallback; callers should provide explicit sample IDs."""
    name = Path(path).name
    if "__" in name:
        return name.split("__", 1)[0]
    for suffix in (".short.coverm.tsv", ".long.coverm.tsv", ".contig_coverm.tsv", ".coverm.tsv"):
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return Path(name).stem


def read_table(path, sample, id_column, seen_features):
    rows = []
    try:
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh, delimiter="\t")
            if not reader.fieldnames:
                raise ValueError(f"{path}: missing TSV header")
            raw_fields = reader.fieldnames
            fields = [field.strip() for field in raw_fields]
            id_col = fields[0]
            mean_col = next((f for f in fields if f.lower().endswith("mean") or f.lower() == "mean"), None)
            tpm_col = next((f for f in fields if f.lower().endswith("tpm") or f.lower() == "tpm"), None)
            rpkm_col = next((f for f in fields if f.lower().endswith("rpkm") or f.lower() == "rpkm"), None)
            for line_number, rec in enumerate(reader, 2):
                normalized = {fields[i]: rec.get(raw_fields[i], "") for i in range(len(fields))}
                feature = (normalized.get(id_col) or "").strip()
                if not feature:
                    continue
                key = (sample, feature)
                if key in seen_features:
                    raise ValueError(
                        f"Duplicate ({sample!r}, {feature!r}) feature in {path}:{line_number}; "
                        f"first seen in {seen_features[key]}"
                    )
                seen_features[key] = f"{path}:{line_number}"
                rows.append({
                    id_column: feature,
                    "sample_id": sample,
                    "rpkm": normalized.get(rpkm_col, "") if rpkm_col else "",
                    "tpm": normalized.get(tpm_col, "") if tpm_col else "",
                    "coverage": normalized.get(mean_col, "") if mean_col else "",
                    "raw_count": "",
                    "mapper": "",
                })
    except OSError as exc:
        raise ValueError(f"Cannot read CoverM table {path}: {exc}") from exc
    return rows


def merge(tables, sample_ids, mapper, id_column, out_path):
    if sample_ids is not None:
        if len(sample_ids) != len(tables):
            raise ValueError(
                f"--sample-ids has {len(sample_ids)} value(s) for {len(tables)} table(s)"
            )
        for sample in sample_ids:
            if not sample.strip():
                raise ValueError("sample IDs must not be empty")
        if len(set(sample_ids)) != len(sample_ids):
            raise ValueError("duplicate sample IDs in --sample-ids")
    else:
        sample_ids = [sample_from_name(path) for path in tables]
        if len(set(sample_ids)) != len(sample_ids):
            raise ValueError("filename inference produced duplicate sample IDs; pass --sample-ids explicitly")

    all_rows = []
    seen_features = {}
    for path, sample in zip(tables, sample_ids):
        all_rows.extend(read_table(path, sample, id_column, seen_features))
    for row in all_rows:
        row["mapper"] = mapper

    columns = [id_column, "sample_id", "rpkm", "tpm", "coverage", "raw_count", "mapper"]
    output = Path(out_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=columns, delimiter="\t")
            writer.writeheader()
            writer.writerows(all_rows)
        os.replace(temporary, output)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return len(all_rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", nargs="*", required=True)
    ap.add_argument("--sample-ids", nargs="*", default=None,
                    help="Sample ID paired by position with each table (recommended)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--mapper", default="")
    ap.add_argument("--id-column", default="contig_id",
                    help="Name of the first output column (use plasmid_id for DESeq2 input)")
    args = ap.parse_args()
    try:
        count = merge(args.tables, args.sample_ids, args.mapper, args.id_column, args.out)
    except (OSError, ValueError, csv.Error) as exc:
        ap.error(str(exc))
    print(f"merged {len(args.tables)} table(s) -> {count} rows", file=sys.stderr)


if __name__ == "__main__":
    main()
