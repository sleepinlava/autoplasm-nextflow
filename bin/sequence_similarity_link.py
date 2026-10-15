#!/usr/bin/env python3
"""Sequence similarity host-plasmid linking.

Compares tetranucleotide composition (cosine similarity) plus GC content of
each plasmid contig against each host MAG bin. This is a simplification of
the ABI internal handler (which also models codon usage). Links are reported
for the best-scoring MAG above ``--min-similarity``.

Output schema follows the ABI ``host_plasmid_links`` standard table.
"""

import argparse
import csv
import math
from itertools import product
from pathlib import Path

KMERS = ["".join(p) for p in product("ACGT", repeat=4)]
KIDX = {k: i for i, k in enumerate(KMERS)}
COMP = str.maketrans("ACGT", "TGCA")


def read_fasta(path):
    name, seq = None, []
    with open(path) as fh:
        for line in fh:
            line = line.rstrip()
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(seq)
                name, seq = line[1:].split()[0], []
            elif name is not None:
                seq.append(line.strip())
    if name is not None:
        yield name, "".join(seq)


def canonical_kmer_vector(seq):
    """Tetranucleotide frequency vector, canonicalized by reverse complement."""
    seq = seq.upper()
    vec = [0.0] * len(KMERS)
    total = 0
    for i in range(len(seq) - 3):
        kmer = seq[i:i + 4]
        rc = kmer.translate(COMP)[::-1]
        canon = min(kmer, rc)
        idx = KIDX.get(canon)
        if idx is not None:
            vec[idx] += 1.0
            total += 1
    if total:
        vec = [v / total for v in vec]
    return vec


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def gc(seq):
    seq = seq.upper()
    return (seq.count("G") + seq.count("C")) / len(seq) if seq else 0.0


def load_taxonomy(path):
    tax = {}
    if not path:
        return tax
    with open(path) as fh:
        for rec in csv.DictReader(fh, delimiter="\t"):
            genome = rec.get("user_genome", "")
            tax[Path(genome).stem] = rec.get("classification", "")
    return tax


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plasmid-contigs", required=True)
    ap.add_argument("--host-genomes", default=None, help="Directory of MAG FASTA bins")
    ap.add_argument("--taxonomy", default=None, help="GTDB-Tk taxonomy TSV (optional)")
    ap.add_argument("--sample-id", default="")
    ap.add_argument("--min-similarity", type=float, default=0.7)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = []
    if args.host_genomes:
        bins = sorted(Path(args.host_genomes).glob("*.fa*"))
        taxonomy = load_taxonomy(args.taxonomy)
        bin_features = {}
        for b in bins:
            seq = "".join(s for _, s in read_fasta(b))
            if not seq:
                continue
            bin_features[b.stem] = (canonical_kmer_vector(seq), gc(seq))
        for cid, seq in read_fasta(args.plasmid_contigs):
            if len(seq) < 1000:
                continue
            pvec, pgc = canonical_kmer_vector(seq), gc(seq)
            best, best_score = None, 0.0
            for bname, (bvec, bgc) in bin_features.items():
                sim = cosine(pvec, bvec)
                gc_penalty = abs(pgc - bgc)
                score = sim * max(0.0, 1.0 - gc_penalty)
                if score > best_score:
                    best, best_score = bname, score
            if best is not None and best_score >= args.min_similarity:
                rows.append([cid, best, args.sample_id, "sequence_similarity",
                             f"{best_score:.4f}",
                             f"taxonomy={taxonomy.get(best, 'NA')};method=tetranucleotide_gc"])

    with open(args.out, "w", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(["plasmid_id", "host_id", "sample_id", "evidence_type", "score", "supporting_data"])
        writer.writerows(rows)
    print(f"sequence similarity links: {len(rows)} link(s)")


if __name__ == "__main__":
    main()
