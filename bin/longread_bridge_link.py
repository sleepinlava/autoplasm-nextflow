#!/usr/bin/env python3
"""Long-read bridge evidence host-plasmid linking.

Parses a SAM alignment (``samtools view`` output of the contig-alignment BAM)
and finds reads that align to both a plasmid contig and a non-plasmid contig
(primary + supplementary alignments). Each such read is one piece of bridge
evidence linking the plasmid to the host contig's bin.

Output schema follows the ABI ``host_plasmid_links`` standard table.
"""

import argparse
import csv
from collections import defaultdict


def read_fasta_ids(path):
    ids = set()
    with open(path) as fh:
        for line in fh:
            if line.startswith(">"):
                ids.add(line[1:].split()[0])
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sam", required=True)
    ap.add_argument("--plasmid-contigs", required=True)
    ap.add_argument("--assembly", required=True)
    ap.add_argument("--sample-id", default="")
    ap.add_argument("--min-reads", type=int, default=2)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    plasmid_ids = read_fasta_ids(args.plasmid_contigs)
    all_ids = read_fasta_ids(args.assembly)

    read_targets = defaultdict(set)
    with open(args.sam) as fh:
        for line in fh:
            if line.startswith("@") or not line.strip():
                continue
            fields = line.split("\t")
            if len(fields) < 3 or fields[2] == "*":
                continue
            flag = int(fields[1])
            if flag & 0x4:  # unmapped
                continue
            read_targets[fields[0]].add(fields[2])

    bridges = defaultdict(int)  # (plasmid, host_contig) -> read count
    for targets in read_targets.values():
        plasmids = targets & plasmid_ids
        hosts = (targets - plasmid_ids) & all_ids
        for p in plasmids:
            for h in hosts:
                bridges[(p, h)] += 1

    with open(args.out, "w", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(["plasmid_id", "host_id", "sample_id", "evidence_type", "score", "supporting_data"])
        for (p, h), n in sorted(bridges.items()):
            if n >= args.min_reads:
                writer.writerow([p, h, args.sample_id, "long_read_bridge", n,
                                 f"bridging_reads={n}"])
    print(f"long-read bridge links: {sum(1 for v in bridges.values() if v >= args.min_reads)} link(s)")


if __name__ == "__main__":
    main()
