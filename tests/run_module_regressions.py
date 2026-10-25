#!/usr/bin/env python3
"""Run isolated Nextflow module regressions with real production modules."""

import argparse
import csv
import gzip
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "tests" / "nextflow" / "nextflow.config"
HARNESS = ROOT / "tests" / "nextflow"
ALL_SUITES = (
    "catalog", "sequence", "sample-ids", "coabundance", "host-routing",
    "sequence-optional", "longread-source", "crispr-guard", "qc", "abricate-routing",
)


class RegressionFailure(RuntimeError):
    pass


def require_tools(names):
    missing = [name for name in names if shutil.which(name) is None]
    if missing:
        raise RegressionFailure(f"未运行：缺少工具 {', '.join(missing)}")


def require_qc_versions():
    """Native QC must exercise the versions declared by its production modules."""
    versions = {}
    for name, pattern in [('fastqc', r'FastQC v(\S+)'),
                          ('multiqc', r'multiqc, version (\S+)'),
                          ('fastp', r'fastp (\S+)')]:
        environment = ROOT / 'modules' / 'nf-core' / name / 'environment.yml'
        declared = re.findall(r'^\s*-\s+bioconda::' + name + r'=([^\s]+)\s*$',
                              environment.read_text(), re.MULTILINE)
        if len(declared) != 1:
            raise RegressionFailure(f'无法确定 {name} 的生产版本：{environment}')
        result = subprocess.run([name, '--version'], text=True, capture_output=True, check=False)
        output = (result.stdout + result.stderr).strip()
        match = re.fullmatch(pattern, output)
        if result.returncode != 0 or match is None or match.group(1) != declared[0]:
            raise RegressionFailure(f'QC 回归要求 {name}=={declared[0]}，实际：{output}（退出码 {result.returncode}）')
        versions[name] = {'expected': declared[0], 'actual': match.group(1),
                          'executable': shutil.which(name), 'version_output': output}
    return versions


def java_version():
    java = str(Path(os.environ["JAVA_HOME"]) / "bin" / "java") if os.environ.get("JAVA_HOME") else shutil.which("java")
    if java is None:
        return "missing"
    result = subprocess.run([java, "-version"], text=True, capture_output=True, check=False)
    return (result.stderr or result.stdout).splitlines()[0] if (result.stderr or result.stdout) else "unknown"


def nextflow_version():
    result = subprocess.run(["nextflow", "-version"], text=True, capture_output=True, check=True)
    output = result.stdout + result.stderr
    # `-version` prints a spaced banner followed by `version 26.x`; older
    # launchers may instead print the one-line `nextflow version 26.x`.
    match = re.search(r"\bversion\s+(\d+)(?:\.[^\s]+)?", output, re.IGNORECASE)
    if not match:
        raise RegressionFailure(f"无法识别 Nextflow 版本：{output.strip()}")
    if int(match.group(1)) != 26:
        raise RegressionFailure(f"模块回归要求 Nextflow 26 严格语法环境，当前为：{output.strip()}")
    return output.strip()


def make_temp(keep):
    path = Path(tempfile.mkdtemp(prefix="autoplasm-module-regression-"))
    return path


def print_artifacts(base):
    print(f"测试工件保留在：{base}", file=sys.stderr)
    for pattern in (".command.sh", ".command.err"):
        for path in sorted(base.rglob(pattern)):
            print(f"  {path}", file=sys.stderr)
    for path in sorted(base.rglob("*.trace")):
        print(f"  trace: {path}", file=sys.stderr)


def env_for_run():
    env = os.environ.copy()
    existing = env.get("PATH", "")
    env["PATH"] = str(ROOT / "bin") + (os.pathsep + existing if existing else "")
    return env


def run_nf(base, harness, fixture_dir, out_dir, work_dir, trace_path,
           params=None, resume=False, expect_success=True):
    for path in (fixture_dir, out_dir, work_dir, trace_path.parent):
        path.mkdir(parents=True, exist_ok=True)
    command = [
        "nextflow", "-C", str(CONFIG), "run", str(HARNESS / harness),
        "--fixture_dir", str(fixture_dir), "--outdir", str(out_dir),
        "-work-dir", str(work_dir), "-with-trace", str(trace_path),
        "-ansi-log", "false",
    ]
    if params:
        # An empty CLI string is treated as a flag by Nextflow. JSON preserves
        # empty IDs, booleans and lists exactly as supplied by each test case.
        param_file = trace_path.with_suffix('.params.json')
        param_file.write_text(json.dumps(params))
        command.extend(['-params-file', str(param_file)])
    if resume:
        command.append("-resume")
    result = subprocess.run(
        command, cwd=ROOT, env=env_for_run(), text=True, capture_output=True,
        check=expect_success,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if not expect_success and result.returncode == 0:
        raise RegressionFailure("Expected Nextflow failure, but workflow exited successfully")
    return result


def assert_duplicate_join_failure(result):
    assert_true(result.returncode != 0, "duplicate-key workflow exited successfully")
    assert_true(re.search(r"Detected join operation duplicate emission on (?:left|right) channel -- offending element:",
                          result.stdout + result.stderr, re.IGNORECASE) is not None,
                "workflow failed without the intended duplicate-key join diagnostic")


def trace_rows(path):
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def trace_statuses(path, process_fragment=None):
    rows = trace_rows(path)
    if process_fragment:
        rows = [row for row in rows if process_fragment.lower() in row.get("name", "").lower()]
    return [row.get("status", "") for row in rows]


def command_files(work_dir):
    return sorted(work_dir.rglob(".command.sh"), key=lambda path: path.stat().st_mtime)


def assert_true(condition, message):
    if not condition:
        raise RegressionFailure(message)


def write_fasta(path, records):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f">{name}\n{sequence}\n" for name, sequence in records))
    return path


def write_coverm(path, values):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        fh.write("Contig\tLength\tCount Mean\tRPKM\tTPM\n")
        for feature, value in values:
            fh.write(f"{feature}\t1200\t{value}\t{value}\t{value}\n")
    return path


def make_catalog_fixture(root):
    root.mkdir(parents=True, exist_ok=True)
    write_fasta(root / "S1.plasmid_contigs.fasta", [("contig_1", "ACGT")])
    write_fasta(root / "S2.plasmid_contigs.fasta", [("contig_1", "TGCA")])
    write_fasta(root / "O'Brien.plasmid_contigs.fasta", [("quoted", "GGGG")])


def suite_catalog(base):
    fixture = base / "fixtures" / "catalog"
    out = base / "out"
    work = base / "work"
    make_catalog_fixture(fixture)
    assert_true(not (out / "04_plasmid_detection" / "consensus").exists(),
                "catalog fixture unexpectedly starts with a consensus publish directory")

    trace1 = base / "trace-first.trace"
    run_nf(base, "catalog.nf", fixture, out, work, trace1)
    output = out / "09_comparative_genomics" / "plasmid_catalog_input.fasta"
    assert_true(output.exists(), "catalog module did not publish its combined FASTA")
    assert_true(">S1|contig_1" in output.read_text() and ">S2|contig_1" in output.read_text() and
                ">O'Brien|quoted" in output.read_text(),
                "catalog output lost sample identity")
    assert_true("COMPLETED" in trace_statuses(trace1, "PLASMID_CATALOG_PREPARE"),
                "catalog process was not recorded as completed")
    scripts = command_files(work)
    assert_true(bool(scripts), "catalog .command.sh was not retained in the work directory")
    command = scripts[-1].read_text()
    assert_true("--contigs" in command and "04_plasmid_detection" not in command and "*.fasta" not in command,
                "catalog command still reads from a publish-directory glob")
    assert_true("'\"'\"'" in command, "catalog command did not shell-quote an apostrophe in an input name")

    stale_dir = out / "04_plasmid_detection" / "consensus"
    stale_dir.mkdir(parents=True)
    write_fasta(stale_dir / "OLD.plasmid_contigs.fasta", [("old", "CCCC")])
    trace2 = base / "trace-cached.trace"
    run_nf(base, "catalog.nf", fixture, out, work, trace2, resume=True)
    assert_true("CACHED" in trace_statuses(trace2, "PLASMID_CATALOG_PREPARE"),
                "unchanged catalog input did not use the Nextflow cache")
    assert_true("OLD|old" not in output.read_text(), "catalog included a stale published sample")

    write_fasta(fixture / "S1.plasmid_contigs.fasta", [("contig_1", "ACGTACGT")])
    trace3 = base / "trace-changed.trace"
    run_nf(base, "catalog.nf", fixture, out, work, trace3, resume=True)
    assert_true("COMPLETED" in trace_statuses(trace3, "PLASMID_CATALOG_PREPARE"),
                "changed FASTA content did not invalidate the catalog cache")
    assert_true("ACGTACGT" in output.read_text(), "catalog output did not update after input change")

    trace4 = base / "trace-cached-again.trace"
    run_nf(base, "catalog.nf", fixture, out, work, trace4, resume=True)
    assert_true("CACHED" in trace_statuses(trace4, "PLASMID_CATALOG_PREPARE"),
                "unchanged updated catalog input did not use the cache")

    empty_fixture = base / "fixtures" / "catalog-empty"
    empty_fixture.mkdir(parents=True)
    empty_trace = base / "trace-empty.trace"
    run_nf(base, "catalog.nf", empty_fixture, base / "out-empty", base / "work-empty", empty_trace,
           {"test_comparative_empty": True})
    assert_true(not trace_statuses(empty_trace, "PLASMID_CATALOG_PREPARE") and
                not trace_statuses(empty_trace, "MMSEQS2"),
                "empty comparative channel scheduled catalog or MMseqs2")
    print("catalog: explicit FASTA dependencies, stale-output isolation, empty input, and resume cache passed")


def suite_sequence(base):
    fixture = base / "fixtures" / "sequence"
    sample = "S1"
    import random
    sequence = "".join(random.Random(39040).choices("ACGT", k=1200))
    write_fasta(fixture / f"{sample}.plasmid_contigs.fasta", [("p1", sequence)])
    write_fasta(fixture / f"{sample}.metabat2_bins" / "bin.1.fa", [("contig_1", sequence)])
    (fixture / f"{sample}.taxonomy.tsv").write_text(
        "user_genome\tclassification\nbin.1.fa\td__Bacteria;p__Example\n"
    )
    out = base / "out"
    work = base / "work"
    trace = base / "trace.trace"
    run_nf(base, "sequence.nf", fixture, out, work, trace,
           {"sample_id": sample, "with_taxonomy": True})
    table = out / "07_host_prediction" / "linking" / "sequence" / f"{sample}.sequence_links.tsv"
    assert_true(table.exists(), "sequence module did not publish its TSV")
    with table.open() as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    assert_true(not rows, "Uncalibrated TETRA emitted host links")
    with (table.parent / f"{sample}.sequence_scores.tsv").open() as fh:
        scores = list(csv.DictReader(fh, delimiter="\t"))
    assert_true(len(scores) == 1 and scores[0]["sample_id"] == sample and scores[0]["host_id"] == "bin.1",
                "nested MetaBAT2 bin directory did not produce the expected composition score")
    assert_true(abs(float(scores[0]["score"]) - 1.0) < 0.001, "matching sequences did not score near one")
    assert_true(scores[0]["association_status"] == "disabled_uncalibrated", "Missing score-only state")
    scripts = command_files(work)
    command = next((path.read_text() for path in scripts if "sequence_similarity_link.R" in path.read_text()), "")
    assert_true("--host-genomes mag_bins" in command,
                "sequence .command.sh does not pass the staged MAG directory")
    assert_true("${params.outdir}" not in command and "mag_bins/*.fa" not in command,
                "sequence task command searched a publish directory or a glob")
    print("sequence: real module staged nested MAG directory and scored without host links")


def suite_sample_ids(base):
    cases = [
        ("valid", "A__B.v1", True, "VALID\tA__B.v1"),
        ("duplicate", "S1,S1", False, "line 3: duplicate sample_id 'S1'"),
        ("empty", "", False, "line 2: sample_id must not be empty"),
        ("whitespace", "bad id", False, "line 2: invalid sample_id 'bad id'"),
        ("path_separator", "bad/id", False, "line 2: invalid sample_id 'bad/id'"),
    ]
    for name, ids, success, expected in cases:
        trace = base / f"trace-{name}.trace"
        result = run_nf(base, "sample_ids.nf", base / "fixtures", base / f"out-{name}",
                        base / f"work-{name}", trace, {"ids": ids}, expect_success=success)
        text = result.stdout + result.stderr
        assert_true(expected in text, f"sample ID case {name} did not report {expected!r}")
    print("sample-ids: valid dotted/double-underscore ID and invalid IDs behaved as specified")


def suite_host_routing(base):
    fixture = base / "fixtures" / "host-routing"
    fixture.mkdir(parents=True)
    for sample in ("S1", "S2"):
        for mate in ("R1", "R2"):
            (fixture / f"{sample}.{mate}.fastq").write_text(f"@{sample}_{mate}\nACGT\n+\nIIII\n")
    out = base / "out"
    trace = base / "trace.trace"
    result = run_nf(base, "host_routing.nf", fixture, out, base / "work", trace)
    routes = [line for line in result.stdout.splitlines() if line.startswith("ROUTE\t")]
    assert_true(set(routes) == {"ROUTE\tS1\t2", "ROUTE\tS2\t2"},
                f"host profile router produced unexpected short-read routes: {routes}")
    hybrid = (ROOT / "subworkflows" / "hybrid.nf").read_text()
    assert_true("HOST_PREDICTION(ch_final_short, Channel.empty(), ch_plasmids" in hybrid,
                "Hybrid still routes long reads into MetaPhlAn")
    for sample in ("illumina", "ont", "pacbio_hifi"):
        source = (ROOT / "subworkflows" / f"{sample}.nf").read_text()
        assert_true("HOST_PREDICTION(" in source, f"{sample} host prediction call disappeared")
    print("host-routing: real profile input adapter emitted one short-read route per Hybrid sample")


def sequence_optional_fixtures(root):
    import random
    seq = ''.join(random.Random(39040).choices('ACGT', k=1200))
    for sample in ("S1", "S2"):
        write_fasta(root / f"{sample}.plasmid_contigs.fasta", [("p1", seq)])
    write_fasta(root / "S1.metabat2_bins" / "bin.1.fa", [("h1", seq)])
    write_fasta(root / "S3.metabat2_bins" / "bin.3.fa", [("h3", seq)])
    for sample, bin_id in (("S1", "bin.1.fa"), ("S4", "bin.4.fa")):
        (root / f"{sample}.taxonomy.tsv").write_text(
            f"user_genome\tclassification\n{bin_id}\td__Bacteria;p__Example\n"
        )


def suite_sequence_optional(base):
    fixture = base / "fixtures" / "sequence-optional"
    sequence_optional_fixtures(fixture)
    scenarios = [
        ("default", {}),
        ("trimmed-list", {"host_linking_methods": [" sequence "]}),
        ("trimmed-string", {"host_linking_methods": " sequence "}),
        ("no-mag", {"omit_mag": True}),
        ("no-taxonomy", {"omit_taxonomy": True}),
        ("no-plasmids", {"empty_plasmids": True}),
    ]
    for name, params in scenarios:
        out, work, trace = base / f"out-{name}", base / f"work-{name}", base / f"trace-{name}.trace"
        execution = run_nf(base, "link_sequence_optional.nf", fixture, out, work, trace, params)
        assert_true("OPTIONAL_LINK\t" not in execution.stdout, "TETRA leaked into unified host links")
        task_statuses = trace_statuses(trace, "LINK_SEQUENCE")
        if name == "no-plasmids":
            assert_true(not task_statuses, "empty plasmid channel scheduled LINK_SEQUENCE")
            continue
        table_dir = out / "07_host_prediction" / "linking" / "sequence"
        assert_true((table_dir / "S1.sequence_links.tsv").exists(), f"{name}: S1 task output missing")
        assert_true((table_dir / "S2.sequence_links.tsv").exists(), f"{name}: S2 task output missing")
        assert_true(not (table_dir / "S3.sequence_links.tsv").exists(), "MAG-only S3 was not filtered")
        assert_true(not (table_dir / "S4.sequence_links.tsv").exists(), "taxonomy-only S4 was not filtered")
        assert_true(len(task_statuses) == 2, f"{name}: expected two plasmid sample tasks, got {task_statuses}")
        if name in ("default", "trimmed-list", "trimmed-string"):
            def scored(sample):
                with (table_dir / f"{sample}.sequence_scores.tsv").open() as stream:
                    return list(csv.DictReader(stream, delimiter="\t"))
            s1, s2 = scored("S1"), scored("S2")
            assert_true(len(s1) == 1 and not s2,
                        "present MAG and absent MAG did not take distinct expected branches")
        for sid in ["S1", "S2"]:
            with (table_dir / f"{sid}.sequence_links.tsv").open() as stream:
                assert_true(not list(csv.DictReader(stream, delimiter="\t")), "Uncalibrated link file is nonempty")
    for key in ("duplicate_keys", "duplicate_mag_keys", "duplicate_taxonomy_keys"):
        duplicate = run_nf(base, "link_sequence_optional.nf", fixture, base / f"out-{key}",
                           base / f"work-{key}", base / f"trace-{key}.trace",
                           {key: True}, expect_success=False)
        assert_duplicate_join_failure(duplicate)
    print("sequence-optional: left-side plasmid filtering, absent MAG/taxonomy, and empty input passed")


def suite_coabundance(base):
    fixture = base / "fixtures" / "coabundance"
    ids = ["A__B.v1", "S.2", "S.1"]
    values = [30, 20, 10]
    for sample, value in zip(ids, values):
        write_coverm(fixture / f"{sample}.coverm.tsv", [("p1", value)])
        additional = "" if sample == "S.1" else "Example species"
        (fixture / f"{sample}.metaphlan.tsv").write_text(
            "#clade_name\tNCBI_tax_id\trelative_abundance\tadditional_species\n"
            f"k__Bacteria|p__Example|g__Genus|s__Example\t1\t{value}\t{additional}\n"
        )
    out, work, trace = base / "out", base / "work", base / "trace.trace"
    run_nf(base, "coabundance.nf", fixture, out, work, trace)
    merged = out / "tables" / "coabundance_plasmid_abundance.tsv"
    assert_true(merged.exists(), "CoverM tables were not merged for co-abundance")
    with merged.open() as fh:
        abundance_rows = list(csv.DictReader(fh, delimiter="\t"))
    assert_true({row["sample_id"] for row in abundance_rows} == set(ids),
                "co-abundance merge lost explicit sample IDs")
    expected_coverage = {"A__B.v1": "30", "S.2": "20", "S.1": "10"}
    assert_true({row["sample_id"]: row["coverage"] for row in abundance_rows} == expected_coverage,
                "sample IDs were detached from their paired CoverM table during collection")
    links = out / "07_host_prediction" / "coabundance_links.tsv"
    assert_true(links.exists(), "co-abundance module did not publish its links table")
    with links.open() as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    assert_true(len(rows) == 1 and abs(float(rows[0]["score"]) - 1.0) < 0.001,
                "three-sample matching profiles did not correlate")
    link_command = next((path.read_text() for path in command_files(work)
                         if "coabundance_link.R" in path.read_text()), "")
    assert_true("--plasmid-abundance" in link_command and "--host-sample-ids" in link_command,
                "co-abundance module command did not pass the merged table and explicit host IDs")
    print("coabundance: real merge module fed one explicit-ID merged table to the linking module")


def sam_record(qname, flag, reference):
    fields = [qname, str(flag), reference, "1", "60", "100M", "*", "0", "0", "A" * 100, "I" * 100]
    return "\t".join(fields) + "\n"


def suite_longread_source(base):
    require_tools(["samtools"])
    fixture = base / "fixtures" / "longread"
    write_fasta(fixture / "S1.plasmid_contigs.fasta", [("p1", "A" * 1200)])
    write_fasta(fixture / "S1.assembly.fasta", [("p1", "A" * 1200), ("h1", "C" * 1200)])
    header = "@HD\tVN:1.6\tSO:unsorted\n@SQ\tSN:p1\tLN:1200\n@SQ\tSN:h1\tLN:1200\n"
    (fixture / "long.sam").write_text(header + "".join(
        sam_record(f"long{i}", flag, ref)
        for i in (1, 2) for flag, ref in ((0, "p1"), (0x800, "h1"))
    ))
    (fixture / "short.sam").write_text(header + sam_record("pair/1", 0x41, "p1") +
                                       sam_record("pair/2", 0x81, "h1"))
    (fixture / "merged.sam").write_text((fixture / "short.sam").read_text() +
                                         "".join(sam_record(f"long{i}", flag, ref)
                                                 for i in (1, 2) for flag, ref in ((0, "p1"), (0x800, "h1"))))
    for stem in ("long", "short", "merged"):
        sam = fixture / f"{stem}.sam"
        subprocess.run(["samtools", "view", "-b", "-o", str(fixture / f"S1.{stem}.bam"), str(sam)],
                       check=True, text=True, capture_output=True)

    out, work, trace = base / "out", base / "work", base / "trace.trace"
    # The harness script's params block loses to the -C config file
    # (params.host_linking_methods = ['sequence'] there), so pin the intended
    # method via the params file, which outranks the config.
    run_nf(base, "longread_source.nf", fixture, out, work, trace,
           {"host_linking_methods": ["long_read"], "host_linking_optional_methods": []})
    links = out / "07_host_prediction" / "linking" / "longread" / "S1.longread_bridge_links.tsv"
    assert_true(links.exists(), "long-read linking module output missing")
    with links.open() as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    assert_true(len(rows) == 1 and rows[0]["host_id"] == "h1" and rows[0]["score"] == "2",
                "long-read bridge did not use the two primary/supplementary reads")
    command = next((path.read_text() for path in command_files(work)
                    if "longread_bridge_link.R" in path.read_text()), "")
    assert_true("S1.long.bam" in command and "S1.merged.bam" not in command and "S1.short.bam" not in command,
                "long-read linking task did not stage only the long-read BAM")
    coverage = (ROOT / "subworkflows" / "contig_coverage.nf").read_text()
    assert_true("long_bam = ch_long_bam" in coverage, "coverage workflow does not emit its independent long-read BAM")
    print("longread-source: real host-linking path consumed long BAM; merged/short BAMs were excluded")


def suite_crispr_guard(base):
    trace = base / "trace-enabled.trace"
    result = run_nf(base, "crispr_guard.nf", base / "fixtures", base / "out-enabled",
                    base / "work-enabled", trace,
                    {"host_linking_methods": [], "host_linking_optional_methods": ["crispr"]},
                    expect_success=False)
    assert_true("CRISPR host-plasmid linking is not implemented" in result.stdout + result.stderr,
                "enabling the unsupported CRISPR branch did not fail explicitly")
    disabled_trace = base / "trace-disabled.trace"
    result = run_nf(base, "crispr_guard.nf", base / "fixtures", base / "out-disabled",
                    base / "work-disabled", disabled_trace,
                    {"host_linking_methods": [], "host_linking_optional_methods": []})
    assert_true("CRISPR host-plasmid linking is not implemented" not in result.stdout + result.stderr,
                "disabled CRISPR branch still raised the unsupported error")
    fixture = base / "fixtures" / "crispr"
    write_fasta(fixture / "S1.plasmid_contigs.fasta", [("p1", "ACGT")])
    write_fasta(fixture / "S1.metabat2_bins" / "bin.1.fa", [("h1", "ACGT")])
    module_trace = base / "trace-module.trace"
    result = run_nf(base, "crispr_guard.nf", fixture, base / "out-module",
                    base / "work-module", module_trace,
                    {"host_linking_optional_methods": [], "direct_module": True}, expect_success=False)
    assert_true("CRISPR host-plasmid linking is not implemented" in result.stdout + result.stderr,
                "direct LINK_CRISPR caller did not receive an explicit unsupported error")
    main_enabled = run_nf(base, "../../main.nf", base / "fixtures", base / "out-main-enabled",
                          base / "work-main-enabled", base / "trace-main-enabled.trace",
                          {"host_plasmid_linking": True, "host_linking_optional_methods": "crispr"},
                          expect_success=False)
    assert_true("CRISPR host-plasmid linking is not implemented" in main_enabled.stdout + main_enabled.stderr,
                "main workflow did not reject CRISPR before unrelated startup validation")
    main_disabled = run_nf(base, "../../main.nf", base / "fixtures", base / "out-main-disabled",
                           base / "work-main-disabled", base / "trace-main-disabled.trace",
                           {"host_plasmid_linking": False, "host_linking_optional_methods": "crispr"},
                           expect_success=False)
    assert_true("CRISPR host-plasmid linking is not implemented" not in
                main_disabled.stdout + main_disabled.stderr,
                "main workflow rejected the CRISPR option while host linking was disabled")
    main_source = (ROOT / "main.nf").read_text()
    assert_true("CRISPR host-plasmid linking is not implemented" in main_source,
                "main workflow no longer rejects CRISPR before database checks")
    print("crispr-guard: enabled method fails clearly; disabled method leaves other branches available")


def write_fastq_gz(path, sample, stage, mate, count):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sequence = "ACGT" * 18 + "ACG"
    quality = "I" * len(sequence)
    with gzip.open(path, "wt") as fh:
        for index in range(count):
            fh.write(f"@{sample}_{stage}_{mate}_{index}\n{sequence}\n+\n{quality}\n")


def make_fastp_json(path):
    # Generate the complete target-version producer format; hand-written partial
    # JSON omitted `command` and was correctly rejected by MultiQC 1.35.
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    input_reads = path.with_suffix('.input.fastq.gz')
    write_fastq_gz(input_reads, 'FASTP', 'raw', 'R1', 200)
    command = ['fastp', '--in1', str(input_reads), '--out1', str(path.with_suffix('.clean.fastq.gz')),
               '--json', str(path), '--html', str(path.with_suffix('.html')), '--thread', '1',
               '--disable_adapter_trimming', '--disable_trim_poly_g']
    result = subprocess.run(command, text=True, capture_output=True, check=True)
    path.with_suffix('.producer.log').write_text(result.stdout + result.stderr)
    data = json.loads(path.read_text())
    assert_true(data['summary']['before_filtering']['total_reads'] == 200 and
                data['summary']['after_filtering']['total_reads'] == 200,
                'real fastp fixture must preserve all 200 known reads')


def make_qc_fixtures(root):
    counts = {
        ("S1", "raw", "R1"): 100, ("S1", "raw", "R2"): 110,
        ("S1", "clean", "R1"): 120, ("S1", "clean", "R2"): 130,
        ("S2", "raw", "R1"): 140, ("S2", "raw", "R2"): 150,
        ("S2", "clean", "R1"): 160, ("S2", "clean", "R2"): 170,
    }
    for (sample, stage, mate), count in counts.items():
        write_fastq_gz(root / sample / stage / f"{mate}.fastq.gz", sample, stage, mate, count)
    return counts


def qc_run(base, fixture, name, run_fastqc, run_multiqc, include_fastp_json, fastp_json=None,
           extra_alias_tests=False):
    out, work, trace = base / f"out-{name}", base / f"work-{name}", base / f"trace-{name}.trace"
    params = {"run_fastqc": run_fastqc, "run_multiqc": run_multiqc,
              "include_fastp_json": include_fastp_json,
              "extra_alias_tests": extra_alias_tests}
    if fastp_json:
        params["fastp_json"] = str(fastp_json)
    run_nf(base, "qc.nf", fixture, out, work, trace, params)
    return out, work, trace


def multiqc_data_text(work, trace):
    rows = trace_rows(trace)
    multiqc_tasks = [row for row in rows if row.get('name', '').split(' (')[0].split(':')[-1] in ['MULTIQC', 'MULTIQC_ONT']]
    assert_true(len(multiqc_tasks) == 1, "Exactly one MultiQC task must be recorded")
    assert_true(bool(multiqc_tasks[0].get('workdir')), 'MultiQC trace lacks workdir; refusing unrelated or stale files')
    task_work = Path(multiqc_tasks[0]['workdir']).resolve()
    assert_true(task_work.is_relative_to(Path(work).resolve()) and task_work.is_dir(),
                'MultiQC task directory must belong to this regression work directory')
    directories = [path for path in task_work.glob('*_data') if path.is_dir()]
    assert_true(len(directories) == 1, "MultiQC task must write exactly one report data directory")
    files = [path for path in directories[0].iterdir() if path.is_file() and path.suffix in ['.txt', '.json', '.log']]
    assert_true(bool(files), "MultiQC task did not write its data files")
    return {path.name: path.read_text() for path in files}


def assert_multiqc_fastqc_sources(work, trace, expected):
    data_files = multiqc_data_text(work, trace)
    assert_true('multiqc_fastqc.txt' in data_files, 'MultiQC did not parse FastQC source data')
    records = list(csv.DictReader(io.StringIO(data_files['multiqc_fastqc.txt']), delimiter='\t'))
    assert_true(len(records) == len(expected), 'MultiQC merged or lost FastQC reports')
    assert_true({row['Sample'] for row in records} == set(expected), 'MultiQC changed sample/stage/mate identities')
    for row in records:
        assert_true(row['Filename'] == row['Sample'], 'MultiQC source filename differs from its complete sample key')
        assert_true(float(row['Total Sequences']) == expected[row['Sample']], 'MultiQC assigned the wrong read count to a source')


def suite_qc(base):
    require_tools(["fastqc", "multiqc", "fastp"])
    versions = require_qc_versions()
    (base / 'tool-versions.json').write_text(json.dumps(versions, indent=2) + '\n')
    print('QC versions: ' + json.dumps(versions))
    for workflow_name in ("illumina", "hybrid"):
        source = (ROOT / "subworkflows" / f"{workflow_name}.nf").read_text()
        assert_true("SHORT_READ_MULTIQC_INPUTS(FASTP.out.json" in source and
                    "SHORT_READ_MULTIQC_INPUTS.out.files" in source,
                    f"{workflow_name} does not use the production short-read MultiQC input router")
    fixture = base / "fixtures" / "qc"
    counts = make_qc_fixtures(fixture)
    full_out, full_work, full_trace = qc_run(base, fixture, "full", True, True, False)
    publish_dir = full_out / "01_qc" / "fastqc"
    zips = sorted(publish_dir.glob("*.zip"))
    htmls = sorted(publish_dir.glob("*.html"))
    assert_true(len(zips) == 8 and len(htmls) == 8,
                f"expected 8 FastQC ZIP and HTML reports, got {len(zips)} and {len(htmls)}")
    expected = {}
    for (sample, stage, mate), count in counts.items():
        expected[f"{sample}.{stage}.{mate}"] = count
    observed = set()
    for archive in zips:
        with zipfile.ZipFile(archive) as zipped:
            data_name = next(name for name in zipped.namelist() if name.endswith("/fastqc_data.txt"))
            content = zipped.read(data_name).decode()
        filename = re.search(r"^Filename\t(.+)$", content, re.MULTILINE)
        total = re.search(r"^Total Sequences\t(\d+)$", content, re.MULTILINE)
        assert_true(filename is not None and total is not None,
                    f"{archive.name}: FastQC internal filename/read count is missing")
        alias = filename.group(1)
        match = re.fullmatch(r"(S[12])\.(raw|clean)\.(R[12])\.fastq(?:\.gz)?", alias)
        assert_true(match is not None, f"unexpected FastQC internal Filename: {alias}")
        key = ".".join(match.groups())
        assert_true(key in expected, f"unexpected sample/stage/mate in FastQC ZIP: {key}")
        assert_true(int(total.group(1)) == expected[key],
                    f"{key}: expected {expected[key]} reads, got {total.group(1)}")
        observed.add(key)
    assert_true(observed == set(expected), f"FastQC ZIPs did not cover all unique sample/stage/mate inputs: {observed}")
    statuses = trace_statuses(full_trace, "FASTQC")
    assert_true(len(statuses) == 4 and all(status == "COMPLETED" for status in statuses),
                f"expected four completed FastQC tasks, got {statuses}")
    report = full_out / "01_qc" / "multiqc_test_report.html"
    assert_true(report.exists(), "MultiQC report was not published")
    assert_multiqc_fastqc_sources(full_work, full_trace, {key + '.fastq.gz': count for key, count in expected.items()})

    resume_trace = base / "trace-full-resume.trace"
    run_nf(base, "qc.nf", fixture, full_out, full_work, resume_trace, resume=True)
    assert_true(len(trace_statuses(resume_trace, "FASTQC")) == 4 and
                all(status == "CACHED" for status in trace_statuses(resume_trace, "FASTQC")),
                "unchanged FastQC inputs did not use the resume cache")
    assert_true(trace_statuses(resume_trace, "MULTIQC") == ["CACHED"],
                "unchanged MultiQC input did not use the resume cache")
    assert_true(len(list(publish_dir.glob("*.zip"))) == 8 and len(list(publish_dir.glob("*.html"))) == 8,
                "resume created duplicate or missing FastQC publications")

    fastp_json = fixture / "fastp.json"
    make_fastp_json(fastp_json)
    no_fastqc_out, no_fastqc_work, no_fastqc_trace = qc_run(base, fixture, "multiqc-without-fastqc", False, True,
                                                True, fastp_json)
    assert_true((no_fastqc_out / "01_qc" / "multiqc_test_report.html").exists(),
                "MultiQC did not run on fastp JSON with run_fastqc=false")
    assert_true(not trace_statuses(no_fastqc_trace, "FASTQC"),
                "FASTQC was scheduled when run_fastqc=false")
    fastp_table = multiqc_data_text(no_fastqc_work, no_fastqc_trace).get('multiqc_fastp.txt')
    assert_true(bool(fastp_table), 'MultiQC must parse the actual fastp JSON when FastQC is disabled')
    fastp_rows = list(csv.DictReader(io.StringIO(fastp_table), delimiter='\t'))
    assert_true(len(fastp_rows) == 1 and fastp_rows[0]['Sample'] == 'fastp.input.fastq.gz',
                'MultiQC changed or lost the real fastp source identity')

    fastqc_only_out, _, fastqc_only_trace = qc_run(base, fixture, "fastqc-without-multiqc", True, False, False)
    assert_true(len(list((fastqc_only_out / "01_qc" / "fastqc").glob("*.zip"))) == 8,
                "FastQC reports were not published when run_multiqc=false")
    assert_true(not trace_statuses(fastqc_only_trace, "MULTIQC"),
                "MultiQC was scheduled when run_multiqc=false")

    def write_extra(path, count, compressed):
        path.parent.mkdir(parents=True, exist_ok=True)
        opener = gzip.open if compressed else open
        mode = "wt" if compressed else "w"
        with opener(path, mode) as fh:
            sequence = "ACGT" * 18 + "ACG"
            quality = "I" * len(sequence)
            for index in range(count):
                fh.write(f"@extra_{index}\n{sequence}\n+\n{quality}\n")

    write_extra(fixture / "same-basename" / "mate1" / "reads.fq.gz", 105, True)
    write_extra(fixture / "same-basename" / "mate2" / "reads.fq.gz", 115, True)
    write_extra(fixture / "uncompressed" / "mate1" / "reads.fastq", 125, False)
    write_extra(fixture / "uncompressed" / "mate2" / "reads.fq", 135, False)
    for sample, first in [('A.clean.B', 145), ('A.clean.C', 165)]:
        write_extra(fixture / sample / 'R1.fastq.gz', first, True)
        write_extra(fixture / sample / 'R2.fastq.gz', first + 10, True)
    alias_out, alias_work, alias_trace = qc_run(base, fixture, "alias-extensions", True, True, False,
                                       extra_alias_tests=True)
    alias_zips = sorted((alias_out / "01_qc" / "fastqc").glob("*.zip"))
    assert_true(len(alias_zips) == 16, f"extension/complex-ID check expected 16 ZIPs, got {len(alias_zips)}")
    alias_counts = {
        "A__B.v1.raw.R1": (105, "A__B.v1.raw.R1.fastq.gz"),
        "A__B.v1.raw.R2": (115, "A__B.v1.raw.R2.fastq.gz"),
        "U1.clean.R1": (125, "U1.clean.R1.fastq"),
        "U1.clean.R2": (135, "U1.clean.R2.fastq"),
        "A.clean.B.raw.R1": (145, "A.clean.B.raw.R1.fastq.gz"),
        "A.clean.B.raw.R2": (155, "A.clean.B.raw.R2.fastq.gz"),
        "A.clean.C.raw.R1": (165, "A.clean.C.raw.R1.fastq.gz"),
        "A.clean.C.raw.R2": (175, "A.clean.C.raw.R2.fastq.gz"),
    }
    seen_aliases = set()
    for archive in alias_zips:
        with zipfile.ZipFile(archive) as zipped:
            data_name = next(name for name in zipped.namelist() if name.endswith("/fastqc_data.txt"))
            content = zipped.read(data_name).decode()
        filename = re.search(r"^Filename\t(.+)$", content, re.MULTILINE)
        total = re.search(r"^Total Sequences\t(\d+)$", content, re.MULTILINE)
        assert_true(filename is not None and total is not None, f"{archive.name}: no FastQC data")
        for key, (count, expected_filename) in alias_counts.items():
            if filename.group(1) == expected_filename:
                assert_true(int(total.group(1)) == count, f"{key}: wrong read count in ZIP")
                seen_aliases.add(key)
    assert_true(seen_aliases == set(alias_counts), "complex ID or FASTQ extension aliases were not preserved")
    assert_true(len(trace_statuses(alias_trace, "FASTQC")) == 8,
                "same-basename/extension run did not execute all eight sample-stage tasks")
    assert_multiqc_fastqc_sources(alias_work, alias_trace,
        {**{key + '.fastq.gz': count for key, count in expected.items()},
         **{filename: count for count, filename in alias_counts.values()}})
    print("qc: real FastQC/MultiQC verified eight unique aliases, ZIP counts, and conditional routing")


def suite_abricate_routing(base):
    from run_abricate_routing import run_checks
    print("abricate-routing: explicit CLI observer; no database search or biological calls")
    assert_true(run_checks(base), "ABRicate input selection or sample/report provenance mismatch")


def run_suite(name, keep_temp):
    requirements = {
        "catalog": ["nextflow"],
        "sequence": ["nextflow"],
        "sample-ids": ["nextflow"],
        "coabundance": ["nextflow"],
        "host-routing": ["nextflow"],
        "sequence-optional": ["nextflow"],
        "longread-source": ["nextflow", "samtools"],
        "crispr-guard": ["nextflow"],
        "qc": ["nextflow", "fastqc", "multiqc", "fastp"],
        "abricate-routing": ["nextflow", "python3"],
    }
    require_tools(requirements[name])
    version = nextflow_version()
    print(f"Nextflow: {version}")
    print(f"Java: {java_version()}")
    print(f"NXF_SYNTAX_PARSER: {os.environ.get('NXF_SYNTAX_PARSER', '<unset>')}")
    base = make_temp(keep_temp)
    success = False
    try:
        {
            "catalog": suite_catalog,
            "sequence": suite_sequence,
            "sample-ids": suite_sample_ids,
            "coabundance": suite_coabundance,
            "host-routing": suite_host_routing,
            "sequence-optional": suite_sequence_optional,
            "longread-source": suite_longread_source,
            "crispr-guard": suite_crispr_guard,
            "qc": suite_qc,
            "abricate-routing": suite_abricate_routing,
        }[name](base)
        success = True
    except (AssertionError, RegressionFailure, subprocess.CalledProcessError, OSError, StopIteration) as exc:
        print(f"{name}: FAILED: {exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError):
            if exc.stdout:
                print(exc.stdout, end="", file=sys.stderr)
            if exc.stderr:
                print(exc.stderr, end="", file=sys.stderr)
        print_artifacts(base)
        raise RegressionFailure(str(exc)) from exc
    finally:
        if success and not keep_temp:
            shutil.rmtree(base, ignore_errors=True)
        else:
            print_artifacts(base)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=[*ALL_SUITES, "all"], required=True)
    parser.add_argument("--keep-temp", action="store_true")
    args = parser.parse_args()
    suites = ALL_SUITES if args.suite == "all" else (args.suite,)
    failures = []
    for suite in suites:
        try:
            print(f"\n=== {suite} ===")
            run_suite(suite, args.keep_temp)
        except RegressionFailure as exc:
            failures.append((suite, str(exc)))
    if failures:
        for suite, error in failures:
            print(f"未运行/失败 {suite}: {error}", file=sys.stderr)
        return 1
    print("所有请求的模块回归均通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
