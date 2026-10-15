#!/usr/bin/env python3
"""Generate the AutoPlasm summary report (Markdown + HTML + methods).

Simplified standalone re-implementation of the ABI ``report_markdown`` node:
scans the published results directory, summarizes per-sample plasmid counts
from the consensus tables, circularity from structure tables, and lists the
available analysis sections.
"""

import argparse
import csv
import html
from datetime import date
from pathlib import Path

WARNING = ("Sequence-based circularity is predictive and should be confirmed from "
           "the assembly graph or read support.")


def count_fasta_records(path):
    try:
        with open(path) as fh:
            return sum(1 for line in fh if line.startswith(">"))
    except OSError:
        return 0


def summarize_consensus(path):
    total = plasmids = 0
    tools = set()
    with open(path) as fh:
        for rec in csv.DictReader(fh, delimiter="\t"):
            total += 1
            if rec.get("plasmid_call") == "plasmid":
                plasmids += 1
                tools.update(t for t in rec.get("supporting_tools", "").split(";") if t)
    return total, plasmids, sorted(tools)


def summarize_structure(path):
    circular = 0
    with open(path) as fh:
        for rec in csv.DictReader(fh, delimiter="\t"):
            if rec.get("is_circular") == "true":
                circular += 1
    return circular


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--platform", default="")
    ap.add_argument("--project-name", default="plasmid_analysis")
    ap.add_argument("--out-prefix", default=".")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    det_dir = outdir / "04_plasmid_detection"
    samples = {}
    consensus_dir = det_dir / "consensus"
    structure_dir = det_dir / "structure"
    if consensus_dir.is_dir():
        for fasta in sorted(consensus_dir.glob("*.plasmid_contigs.fasta")):
            sid = fasta.name.split(".plasmid_contigs.fasta")[0]
            entry = {"contigs": count_fasta_records(fasta),
                     "total": 0, "plasmids": 0, "tools": [], "circular": 0}
            cons = consensus_dir / f"{sid}.plasmid_consensus.tsv"
            if cons.is_file():
                entry["total"], entry["plasmids"], entry["tools"] = summarize_consensus(cons)
            struct = structure_dir / f"{sid}.plasmid_structure.tsv"
            if struct.is_file():
                entry["circular"] = summarize_structure(struct)
            samples[sid] = entry

    sections = {
        "01_qc": (outdir / "01_qc").is_dir(),
        "02_assembly": (outdir / "02_assembly").is_dir(),
        "03_assembly_qc": (outdir / "03_assembly_qc").is_dir(),
        "04_plasmid_detection": det_dir.is_dir(),
        "05_plasmid_binning": (outdir / "05_plasmid_binning").is_dir(),
        "06_plasmid_typing": (outdir / "06_plasmid_typing").is_dir(),
        "07_host_prediction": (outdir / "07_host_prediction").is_dir(),
        "08_annotation": (outdir / "08_annotation").is_dir(),
        "09_comparative_genomics": (outdir / "09_comparative_genomics").is_dir(),
        "10_abundance": (outdir / "10_abundance").is_dir(),
        "11_diversity": (outdir / "11_diversity").is_dir(),
        "12_network": (outdir / "12_network").is_dir(),
    }

    lines = [
        f"# AutoPlasm report — {args.project_name}",
        "",
        f"- Platform: `{args.platform}`",
        f"- Date: {date.today().isoformat()}",
        f"- Samples: {len(samples)}",
        "",
        "## Plasmid detection summary",
        "",
        "| sample_id | consensus_plasmids | circular | detection_tools |",
        "|---|---|---|---|",
    ]
    for sid, e in samples.items():
        lines.append(f"| {sid} | {e['contigs']} | {e['circular']} | {', '.join(e['tools'])} |")
    lines += ["", "## Analysis sections", ""]
    for name, present in sections.items():
        lines.append(f"- {'[x]' if present else '[ ]'} `{name}`")
    lines += [
        "",
        "## Limitations",
        "",
        f"- {WARNING}",
        "- Plasmid calls are predictions from automated classifiers; confirm "
        "biologically important hits manually.",
        "",
    ]
    md = "\n".join(lines)

    out_prefix = Path(args.out_prefix)
    (out_prefix / "report.md").write_text(md)

    body = "\n".join(
        f"<p>{html.escape(line)}</p>" if not line.startswith("|") else
        f"<pre>{html.escape(line)}</pre>" for line in md.splitlines() if line.strip()
    )
    (out_prefix / "report.html").write_text(
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>AutoPlasm report — {html.escape(args.project_name)}</title>"
        "<style>body{font-family:sans-serif;max-width:60em;margin:2em auto}</style>"
        f"</head><body><pre>{html.escape(md)}</pre></body></html>\n")

    methods = (
        "# Methods\n\n"
        "Metagenomic plasmid analysis was performed with AutoPlasm (Nextflow DSL2 "
        "implementation). Reads were quality-filtered (fastp for short reads; "
        "NanoPlot/Filtlong for ONT; HiFiAdapterFilt for PacBio HiFi). Assembly used "
        "platform-appropriate assemblers (MEGAHIT/metaSPAdes, metaFlye, "
        "hifiasm-meta, OPERA-MS/hybridSPAdes). Plasmid contigs were detected with "
        "geNomad and integrated across tools by consensus voting "
        f"({args.platform} platform). Typing used PlasmidFinder and MOB-typer; "
        "annotation used Bakta, AMRFinderPlus, ISEScan and IntegronFinder. "
        "Abundance was estimated with CoverM.\n")
    (out_prefix / "methods.md").write_text(methods)
    print("report generated: report.md, report.html, methods.md")


if __name__ == "__main__":
    main()
