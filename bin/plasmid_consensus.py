#!/usr/bin/env python3
"""Build consensus plasmid calls across detection tools.

Implements the ABI internal handler ``metagenomic_plasmid.plasmid_consensus``
as a standalone script. Strategies: intersection, majority_vote,
weighted_vote (default), single_tool (primary tool = geNomad).

geNomad is mandatory; additional tool outputs are passed via repeated
``--extra`` arguments and are identified by filename pattern:
``*.plasme.tsv``, ``*.plasx.tsv``, ``*.platon.tsv``, ``*.scapp.fasta``.
"""

import argparse
import csv
import math
import re
import sys
from pathlib import Path

ID_COLUMNS = ("contig_id", "contig", "seq_name", "sequence", "qseqid", "id", "name", "ID")
SCORE_COLUMNS = ("plasmid_score", "plasme_score", "plasx_score", "score", "probability", "prob")
CLASS_COLUMNS = ("classification", "prediction", "label", "class", "verdict")
POSITIVE_LABELS = {"plasmid", "1", "true", "yes", "positive", "plas"}
NEGATIVE_LABELS = {
    "chromosome", "chromosomal", "0", "false", "no", "negative",
    "non plasmid", "not plasmid",
}


def read_fasta(path):
    """Yield (id, sequence) records from a FASTA file."""
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


def sniff_table(path):
    """Parse a delimited prediction file; return list of dict rows."""
    text = Path(path).read_text()
    if not text.strip():
        return []
    first = text.splitlines()[0]
    delimiter = "," if first.count(",") > first.count("\t") else "\t"
    return list(csv.DictReader(text.splitlines(), delimiter=delimiter))


def pick_column(fieldnames, candidates):
    lowered = {f.lower(): f for f in fieldnames or []}
    for cand in candidates:
        if cand.lower() in lowered:
            return lowered[cand.lower()]
    return None


def parse_classification(value, tool_id, path, line_number):
    """Parse one complete classification label without substring guessing."""
    normalized = re.sub(r"[\s_-]+", " ", (value or "").strip().lower())
    if normalized in POSITIVE_LABELS:
        return True
    if normalized in NEGATIVE_LABELS:
        return False
    raise ValueError(
        f"Unsupported classification label {value!r} from {tool_id} at {path}:{line_number}"
    )


def parse_generic_predictions(path, tool_id):
    """Return {contig_id: (score, is_plasmid)} from a tabular prediction file."""
    rows = sniff_table(path)
    if not rows:
        return {}
    fields = list(rows[0].keys())
    id_col = pick_column(fields, ID_COLUMNS) or fields[0]
    score_col = pick_column(fields, SCORE_COLUMNS)
    class_col = pick_column(fields, CLASS_COLUMNS)
    out = {}
    for line_number, row in enumerate(rows, 2):
        cid = (row.get(id_col) or "").strip()
        if not cid:
            continue
        try:
            score = float(row.get(score_col) or 1.0) if score_col else 1.0
        except ValueError:
            score = 1.0
        if class_col:
            is_plasmid = parse_classification(row.get(class_col), tool_id, path, line_number)
        else:
            # Files like Platon's TSV only list plasmid-positive contigs.
            is_plasmid = True
        out[cid] = (score, is_plasmid)
    return out


def parse_genomad(path):
    """geNomad plasmid summary: all listed contigs are plasmid calls."""
    rows = sniff_table(path)
    if not rows:
        return {}
    fields = list(rows[0].keys())
    id_col = pick_column(fields, ("seq_name",)) or fields[0]
    score_col = pick_column(fields, ("plasmid_score",))
    out = {}
    for row in rows:
        cid = (row.get(id_col) or "").strip()
        if not cid:
            continue
        try:
            score = float(row.get(score_col)) if score_col and row.get(score_col) else 1.0
        except ValueError:
            score = 1.0
        out[cid] = (score, True)
    return out


def parse_scapp(path):
    return {cid: (1.0, True) for cid, _ in read_fasta(path)}


def identify_extra(path):
    name = Path(path).name.lower()
    if ".plasme." in name:
        return "plasme"
    if ".plasx." in name:
        return "plasx"
    if ".platon." in name:
        return "platon"
    if ".scapp." in name or "confident_cycs" in name:
        return "scapp"
    return None


def parse_weights(spec):
    weights = {}
    for item in (spec or "").split(","):
        if ":" in item:
            key, _, value = item.partition(":")
            try:
                weights[key.strip()] = float(value)
            except ValueError:
                pass
    return weights


def gc_content(seq):
    if not seq:
        return 0.0
    s = seq.upper()
    return (s.count("G") + s.count("C")) / len(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assembly", required=True)
    ap.add_argument("--genomad-summary", required=True)
    ap.add_argument("--extra", action="append", default=[])
    ap.add_argument("--method", default="weighted_vote",
                    choices=["intersection", "majority_vote", "weighted_vote", "single_tool"])
    ap.add_argument("--weights", default="genomad:0.6,platon:0.15,plasme:0.15,plasx:0.1")
    ap.add_argument("--sample-id", default="")
    ap.add_argument("--out-fasta", required=True)
    ap.add_argument("--out-predictions", required=True)
    ap.add_argument("--out-consensus", required=True)
    args = ap.parse_args()

    # contig -> length/gc from the source assembly
    contig_info = {cid: (len(seq), gc_content(seq)) for cid, seq in read_fasta(args.assembly)}

    try:
        calls = {"genomad": parse_genomad(args.genomad_summary)}
        for extra in args.extra:
            tool = identify_extra(extra)
            if tool is None:
                print(f"warning: unrecognized extra prediction file {extra}", file=sys.stderr)
                continue
            if tool == "scapp":
                calls[tool] = parse_scapp(extra)
            else:
                calls[tool] = parse_generic_predictions(extra, tool)
    except ValueError as exc:
        ap.error(str(exc))

    weights = parse_weights(args.weights)
    active = list(calls.keys())
    all_contigs = sorted({cid for c in calls.values() for cid in c})

    predictions_rows = []
    for tool in active:
        for cid, (score, is_plasmid) in sorted(calls[tool].items()):
            length, gc = contig_info.get(cid, ("", ""))
            predictions_rows.append({
                "contig_id": cid, "sample_id": args.sample_id, "tool_id": tool,
                "plasmid_score": f"{score:.4g}", "classification": "plasmid" if is_plasmid else "chromosome",
                "length": length, "gc_content": f"{gc:.4f}" if gc != "" else "",
            })

    positives = {tool: {cid for cid, (_, is_p) in c.items() if is_p} for tool, c in calls.items()}
    total_weight = sum(weights.get(t, 1.0) for t in active)
    n_active = len(active)

    consensus_rows = []
    for cid in all_contigs:
        supporting = [t for t in active if cid in positives[t]]
        conflicting = [t for t in active if cid not in positives[t]]
        if args.method == "intersection":
            call = len(supporting) == n_active
        elif args.method == "majority_vote":
            call = len(supporting) > n_active / 2
        elif args.method == "single_tool":
            call = cid in positives["genomad"]
        else:  # weighted_vote
            w = sum(weights.get(t, 1.0) for t in supporting)
            call = (w / total_weight) >= 0.5 if total_weight > 0 else False
        length, gc = contig_info.get(cid, ("", ""))
        consensus_rows.append({
            "contig_id": cid, "sample_id": args.sample_id,
            "plasmid_call": "plasmid" if call else "chromosome",
            "supporting_tools": ";".join(supporting),
            "conflicting_tools": ";".join(conflicting),
            "consensus_method": args.method,
            "length": length, "gc_content": f"{gc:.4f}" if gc != "" else "",
        })

    keep = {r["contig_id"] for r in consensus_rows if r["plasmid_call"] == "plasmid"}
    with open(args.out_fasta, "w") as out:
        for cid, seq in read_fasta(args.assembly):
            if cid in keep:
                out.write(f">{cid}\n")
                for i in range(0, len(seq), 80):
                    out.write(seq[i:i + 80] + "\n")

    with open(args.out_predictions, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["contig_id", "sample_id", "tool_id", "plasmid_score",
                                                "classification", "length", "gc_content"], delimiter="\t")
        writer.writeheader()
        writer.writerows(predictions_rows)

    with open(args.out_consensus, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["contig_id", "sample_id", "plasmid_call", "supporting_tools",
                                                "conflicting_tools", "consensus_method", "length", "gc_content"],
                                delimiter="\t")
        writer.writeheader()
        writer.writerows(consensus_rows)

    print(f"consensus: {len(keep)}/{len(consensus_rows)} contigs called plasmid "
          f"({args.method}, tools: {', '.join(active)})")


if __name__ == "__main__":
    main()
