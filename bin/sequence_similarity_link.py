#!/usr/bin/env python3
"""Link plasmid contigs to first-level MAG FASTA files by sequence composition.

The score combines canonical tetranucleotide cosine similarity and a GC
content penalty. This remains a simplified heuristic, not a taxonomic or
whole-genome alignment method.
"""

import argparse
import csv
import math
import sys
from itertools import product
from pathlib import Path

KMERS = ["".join(p) for p in product("ACGT", repeat=4)]
KIDX = {k: i for i, k in enumerate(KMERS)}
COMP = str.maketrans("ACGT", "TGCA")
FASTA_SUFFIXES = {".fa", ".fna", ".fasta"}
COMPRESSED_SUFFIXES = {".fa.gz", ".fna.gz", ".fasta.gz"}


def read_fasta(path):
    name, seq = None, []
    try:
        with open(path, encoding="utf-8") as fh:
            for line_number, line in enumerate(fh, 1):
                line = line.rstrip("\r\n")
                if line.startswith(">"):
                    if name is not None:
                        yield name, "".join(seq)
                    header = line[1:].strip()
                    if not header:
                        raise ValueError(f"{path}:{line_number}: empty FASTA header")
                    name, seq = header.split()[0], []
                elif line.strip():
                    if name is None:
                        raise ValueError(f"{path}:{line_number}: sequence data before FASTA header")
                    seq.append(line.strip())
            if name is not None:
                yield name, "".join(seq)
    except OSError as exc:
        raise ValueError(f"Cannot read FASTA {path}: {exc}") from exc


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
    try:
        with open(path, encoding="utf-8") as fh:
            for rec in csv.DictReader(fh, delimiter="\t"):
                genome = rec.get("user_genome", "")
                if genome:
                    tax[Path(genome).stem] = rec.get("classification", "")
    except OSError as exc:
        raise ValueError(f"Cannot read taxonomy TSV {path}: {exc}") from exc
    return tax


def mag_candidates(directory):
    """Return supported first-level regular files/symlinks, never recurse."""
    path = Path(directory)
    if not path.exists():
        raise ValueError(f"MAG path does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"MAG path is not a directory: {path}")
    candidates = []
    compressed = []
    for item in sorted(path.iterdir(), key=lambda p: p.name):
        lower = item.name.lower()
        if item.is_file() and item.suffix.lower() in FASTA_SUFFIXES:
            candidates.append(item)
        elif item.is_file() and any(lower.endswith(suffix) for suffix in COMPRESSED_SUFFIXES):
            compressed.append(item)
    if not candidates and compressed:
        names = ", ".join(str(item) for item in compressed)
        raise ValueError(f"Compressed MAG FASTA is not supported yet: {names}")
    return candidates


def load_bins(files):
    features = {}
    owners = {}
    for path in files:
        host_id = path.stem
        if host_id in owners:
            raise ValueError(
                f"Duplicate MAG host_id {host_id!r}: {owners[host_id]} and {path}"
            )
        owners[host_id] = path
        seq = "".join(sequence for _, sequence in read_fasta(path))
        if seq:
            features[host_id] = (canonical_kmer_vector(seq), gc(seq))
    return features


def write_output(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(["plasmid_id", "host_id", "sample_id", "evidence_type", "score", "supporting_data"])
        writer.writerows(rows)


def run(args):
    if not math.isfinite(args.min_similarity) or args.min_similarity < 0 or args.min_similarity > 1:
        raise ValueError("--min-similarity must be between 0 and 1")
    if args.host_genomes:
        files = mag_candidates(args.host_genomes)
        bins = load_bins(files)
        taxonomy = load_taxonomy(args.taxonomy)
    else:
        files, bins, taxonomy = [], {}, {}

    plasmids = list(read_fasta(args.plasmid_contigs))
    participating = [(cid, seq) for cid, seq in plasmids if len(seq) >= 1000]
    rows = []
    if bins:
        for cid, seq in participating:
            pvec, pgc = canonical_kmer_vector(seq), gc(seq)
            best, best_score = None, 0.0
            for bname, (bvec, bgc) in bins.items():
                sim = cosine(pvec, bvec)
                score = sim * max(0.0, 1.0 - abs(pgc - bgc))
                if score > best_score:
                    best, best_score = bname, score
            if best is not None and best_score >= args.min_similarity:
                rows.append([cid, best, args.sample_id, "sequence_similarity",
                             f"{best_score:.4f}",
                             f"taxonomy={taxonomy.get(best, 'NA')};method=tetranucleotide_gc"])

    write_output(args.out, rows)
    mag_path = args.host_genomes or "not provided"
    print(
        f"MAG path: {mag_path}; candidate FASTA files: {len(files)}; "
        f"valid bins: {len(bins)}; plasmids compared: {len(participating) if bins else 0}; "
        f"links: {len(rows)}" + ("; MAG input not provided" if not args.host_genomes else ""),
        file=sys.stderr,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plasmid-contigs", required=True)
    ap.add_argument("--host-genomes", default=None, help="Directory of first-level MAG FASTA bins")
    ap.add_argument("--taxonomy", default=None, help="GTDB-Tk taxonomy TSV (optional)")
    ap.add_argument("--sample-id", default="")
    ap.add_argument("--min-similarity", type=float, default=0.7)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    try:
        run(args)
    except (OSError, ValueError, csv.Error) as exc:
        ap.error(str(exc))


if __name__ == "__main__":
    main()
