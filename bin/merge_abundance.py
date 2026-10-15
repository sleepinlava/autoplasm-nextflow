#!/usr/bin/env python3
"""Merge per-sample CoverM contig tables into one long-format abundance table.

CoverM is run with ``--methods mean tpm rpkm``; the sample id is derived from
the staged file name (``<sample>__*.tsv`` when renamed upstream, otherwise the
leading token of the file name).

Output schema follows the ABI ``abundance`` standard table:
contig_id, sample_id, rpkm, tpm, coverage, raw_count, mapper
"""

import argparse
import csv
import sys
from pathlib import Path


def sample_from_name(path):
    name = Path(path).name
    if "__" in name:
        return name.split("__")[0]
    return name.split(".")[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mapper", default="")
    ap.add_argument("--id-column", default="contig_id",
                    help="Name of the first output column (use plasmid_id for DESeq2 input)")
    args = ap.parse_args()

    rows = []
    for path in args.tables:
        sample = sample_from_name(path)
        with open(path) as fh:
            reader = csv.DictReader(fh, delimiter="\t")
            if reader.fieldnames is None:
                continue
            fields = [f.strip() for f in reader.fieldnames]
            id_col = fields[0]
            mean_col = next((f for f in fields if f.lower().endswith("mean") or f.lower() == "mean"), None)
            tpm_col = next((f for f in fields if f.lower().endswith("tpm") or f.lower() == "tpm"), None)
            rpkm_col = next((f for f in fields if f.lower().endswith("rpkm") or f.lower() == "rpkm"), None)
            for rec in reader:
                cid = (rec.get(id_col) or rec.get(reader.fieldnames[0]) or "").strip()
                if not cid:
                    continue
                rows.append({
                    args.id_column: cid,
                    "sample_id": sample,
                    "rpkm": rec.get(rpkm_col, "") if rpkm_col else "",
                    "tpm": rec.get(tpm_col, "") if tpm_col else "",
                    "coverage": rec.get(mean_col, "") if mean_col else "",
                    "raw_count": "",
                    "mapper": args.mapper,
                })

    with open(args.out, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=[args.id_column, "sample_id", "rpkm", "tpm",
                                                "coverage", "raw_count", "mapper"], delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    print(f"merged {len(args.tables)} table(s) -> {len(rows)} rows", file=sys.stderr)


if __name__ == "__main__":
    main()
