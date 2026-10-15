#!/usr/bin/env python3
"""Count long-read primary/supplementary alignments bridging two contigs.

The reported host identifier is an assembly contig ID. This script does not
map host contigs to MAG bins.
"""

import argparse
import csv
import sys
from collections import defaultdict

EXCLUDED_FLAGS = 0x4 | 0x100 | 0x200 | 0x400 | 0x1


def read_fasta_ids(path):
    ids = set()
    try:
        with open(path, encoding="utf-8") as fh:
            for line_number, line in enumerate(fh, 1):
                if line.startswith(">"):
                    header = line[1:].strip()
                    if not header:
                        raise ValueError(f"{path}:{line_number}: empty FASTA header")
                    ids.add(header.split()[0])
    except OSError as exc:
        raise ValueError(f"Cannot read FASTA {path}: {exc}") from exc
    return ids


def parse_sam(path):
    read_targets = defaultdict(lambda: {"primary": set(), "supplementary": set()})
    filtered = defaultdict(int)
    accepted_records = 0
    try:
        with open(path, encoding="utf-8") as fh:
            for line_number, line in enumerate(fh, 1):
                if line.startswith("@") or not line.strip():
                    continue
                fields = line.rstrip("\r\n").split("\t")
                if len(fields) < 11:
                    raise ValueError(f"{path}:{line_number}: SAM record has fewer than 11 fields")
                try:
                    flag = int(fields[1])
                except ValueError as exc:
                    raise ValueError(f"{path}:{line_number}: FLAG is not an integer") from exc
                if flag < 0:
                    raise ValueError(f"{path}:{line_number}: FLAG must be non-negative")
                if flag & 0x4:
                    filtered["unmapped"] += 1
                    continue
                if flag & 0x100:
                    filtered["secondary"] += 1
                    continue
                if flag & 0x200:
                    filtered["qcfail"] += 1
                    continue
                if flag & 0x400:
                    filtered["duplicate"] += 1
                    continue
                if flag & 0x1:
                    filtered["paired"] += 1
                    continue
                if fields[2] == "*":
                    raise ValueError(f"{path}:{line_number}: mapped record has no reference name")
                kind = "supplementary" if flag & 0x800 else "primary"
                read_targets[fields[0]][kind].add(fields[2])
                accepted_records += 1
    except OSError as exc:
        raise ValueError(f"Cannot read SAM {path}: {exc}") from exc
    return read_targets, filtered, accepted_records


def run(args):
    if args.min_reads < 1:
        raise ValueError("--min-reads must be a positive integer")
    plasmid_ids = read_fasta_ids(args.plasmid_contigs)
    assembly_ids = read_fasta_ids(args.assembly)
    read_targets, filtered, accepted_records = parse_sam(args.sam)

    bridges = defaultdict(set)  # (plasmid, host_contig) -> distinct QNAMEs
    bridge_reads = 0
    for qname, alignments in read_targets.items():
        primary = alignments["primary"]
        supplementary = alignments["supplementary"]
        if not primary or not supplementary:
            continue
        bridge_reads += 1
        targets = primary | supplementary
        plasmids = targets & plasmid_ids
        hosts = (targets - plasmid_ids) & assembly_ids
        for plasmid in plasmids:
            for host in hosts:
                bridges[(plasmid, host)].add(qname)

    rows = []
    for (plasmid, host), qnames in sorted(bridges.items()):
        count = len(qnames)
        if count >= args.min_reads:
            rows.append([plasmid, host, args.sample_id, "long_read_bridge", count,
                         f"bridging_reads={count};host_id_type=contig"])

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(["plasmid_id", "host_id", "sample_id", "evidence_type", "score", "supporting_data"])
        writer.writerows(rows)
    filtered_text = ", ".join(f"{name}={count}" for name, count in sorted(filtered.items())) or "none"
    print(
        f"SAM: {args.sam}; accepted long-read alignments: {accepted_records}; "
        f"reads with primary and supplementary records: {bridge_reads}; "
        f"filtered records: {filtered_text}; bridges: {len(rows)}",
        file=sys.stderr,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sam", required=True)
    ap.add_argument("--plasmid-contigs", required=True)
    ap.add_argument("--assembly", required=True)
    ap.add_argument("--sample-id", default="")
    ap.add_argument("--min-reads", type=int, default=2)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    try:
        run(args)
    except (OSError, ValueError, csv.Error) as exc:
        ap.error(str(exc))


if __name__ == "__main__":
    main()
