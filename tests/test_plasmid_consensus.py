import csv
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "plasmid_consensus.R"


class PlasmidConsensusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def run_script(self, *args):
        return subprocess.run(
            ["Rscript", str(SCRIPT), *map(str, args)],
            text=True, capture_output=True, check=False,
        )

    def label_case_files(self, label):
        """Minimal assembly + empty geNomad summary + one plasme row."""
        assembly = self.root / "assembly.fasta"
        assembly.write_text(">p1\nACGT\n")
        summary = self.root / "genomad.tsv"
        summary.write_text("seq_name\tplasmid_score\n")
        extra = self.root / "S1.plasme.tsv"
        extra.write_text(f"contig_id\tclassification\np1\t{label}\n")
        return assembly, summary, extra

    def run_label_case(self, label):
        assembly, summary, extra = self.label_case_files(label)
        predictions = self.root / "predictions.tsv"
        result = self.run_script(
            "--assembly", assembly, "--genomad-summary", summary,
            "--extra", extra, "--sample-id", "S1",
            "--out-fasta", self.root / "out.fa",
            "--out-predictions", predictions,
            "--out-consensus", self.root / "cons.tsv",
        )
        return result, predictions

    def test_explicit_positive_and_negative_labels_use_complete_tokens(self):
        positives = ["plasmid", "  PLASMID  ", "1", "true", "yes", "positive", "plas"]
        negatives = ["chromosome", "chromosomal", "0", "false", "no", "negative",
                     "non-plasmid", "non_plasmid", "not plasmid", " NOT__PLASMID "]
        for value in positives:
            with self.subTest(value=value):
                result, predictions = self.run_label_case(value)
                self.assertEqual(result.returncode, 0, result.stderr)
                with predictions.open() as fh:
                    rows = list(csv.DictReader(fh, delimiter="\t"))
                self.assertEqual(rows[0]["classification"], "plasmid")
        for value in negatives:
            with self.subTest(value=value):
                result, predictions = self.run_label_case(value)
                self.assertEqual(result.returncode, 0, result.stderr)
                with predictions.open() as fh:
                    rows = list(csv.DictReader(fh, delimiter="\t"))
                self.assertEqual(rows[0]["classification"], "chromosome")

    def test_near_matches_and_unknown_labels_fail_with_context(self):
        for value in ("10", "plasmid-like", "unknown", "unclassified", ""):
            with self.subTest(value=value):
                result, _ = self.run_label_case(value)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"plasme at {self.root / 'S1.plasme.tsv'}:2", result.stderr)

    def test_positive_only_table_contract_remains_supported(self):
        assembly = self.root / "assembly.fasta"
        assembly.write_text(">p1\nACGT\n")
        summary = self.root / "genomad.tsv"
        summary.write_text("seq_name\tplasmid_score\n")
        platon = self.root / "sample.platon.tsv"
        platon.write_text("contig_id\tscore\np1\t0.8\n")
        predictions = self.root / "predictions.tsv"
        result = self.run_script(
            "--assembly", assembly, "--genomad-summary", summary,
            "--extra", platon, "--sample-id", "S1",
            "--out-fasta", self.root / "out.fa",
            "--out-predictions", predictions,
            "--out-consensus", self.root / "cons.tsv",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        with predictions.open() as fh:
            rows = [row for row in csv.DictReader(fh, delimiter="\t")
                    if row["tool_id"] == "platon"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(float(rows[0]["plasmid_score"]), 0.8)
        self.assertEqual(rows[0]["classification"], "plasmid")

    def test_negative_classification_does_not_enter_final_consensus_fasta(self):
        assembly = self.root / "assembly.fasta"
        summary = self.root / "genomad.tsv"
        extra = self.root / "S1.plasme.tsv"
        out_fasta = self.root / "plasmids.fasta"
        predictions = self.root / "predictions.tsv"
        consensus = self.root / "consensus.tsv"
        assembly.write_text(">p1\n" + "ACGT" * 300 + "\n")
        summary.write_text("seq_name\tplasmid_score\np1\t0.9\n")
        extra.write_text("contig_id\tclassification\tplasmid_score\np1\tnon-plasmid\t0.1\n")
        result = self.run_script(
            "--assembly", assembly, "--genomad-summary", summary,
            "--extra", extra, "--method", "weighted_vote",
            "--weights", "genomad:0.1,plasme:0.9", "--sample-id", "S1",
            "--out-fasta", out_fasta, "--out-predictions", predictions,
            "--out-consensus", consensus,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(out_fasta.read_text(), "")
        with consensus.open() as fh:
            rows = list(csv.DictReader(fh, delimiter="\t"))
        self.assertEqual(rows[0]["plasmid_call"], "chromosome")

    def test_unknown_cli_classification_fails_with_file_and_line(self):
        assembly = self.root / "assembly.fasta"
        summary = self.root / "genomad.tsv"
        extra = self.root / "S1.plasme.tsv"
        assembly.write_text(">p1\nACGT\n")
        summary.write_text("seq_name\tplasmid_score\n")
        extra.write_text("contig_id\tclassification\np1\tunknown\n")
        result = self.run_script(
            "--assembly", assembly, "--genomad-summary", summary,
            "--extra", extra,
            "--out-fasta", self.root / "out.fa",
            "--out-predictions", self.root / "pred.tsv",
            "--out-consensus", self.root / "cons.tsv",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"Unsupported classification label 'unknown' from plasme at {extra}:2", result.stderr)

    def run_consensus(self, assembly_text, summary_text, extras, weights=None, method="weighted_vote"):
        assembly = self.root / "assembly.fasta"
        summary = self.root / "genomad.tsv"
        out_fasta = self.root / "plasmids.fasta"
        predictions = self.root / "predictions.tsv"
        consensus = self.root / "consensus.tsv"
        assembly.write_text(assembly_text)
        summary.write_text(summary_text)
        args = ["--assembly", assembly, "--genomad-summary", summary,
                "--method", method, "--sample-id", "S1",
                "--out-fasta", out_fasta, "--out-predictions", predictions,
                "--out-consensus", consensus]
        for extra in extras:
            path = self.root / extra[0]
            path.write_text(extra[1])
            args += ["--extra", path]
        if weights:
            args += ["--weights", weights]
        result = self.run_script(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        with consensus.open() as fh:
            return list(csv.DictReader(fh, delimiter="\t"))

    def test_ensemble_columns_track_per_tool_calls(self):
        rows = self.run_consensus(
            ">p1\n" + "ACGT" * 300 + "\n",
            "seq_name\tplasmid_score\np1\t0.99\n",
            [("S1.plasme.tsv", "contig_id\tclassification\tplasmid_score\np1\tchromosome\t0.2\n"),
             ("S1.platon.tsv", "contig_id\tscore\np1\t0.9\n")],
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["genomad"], "plasmid")
        self.assertEqual(row["plasme"], "chromosome")
        self.assertEqual(row["platon"], "plasmid")
        self.assertEqual(row["plasmid_count"], "2")
        # 3 active tools, 2 plasmid calls -> majority plasmid
        self.assertEqual(row["combined_prediction"], "plasmid")

    def test_combined_prediction_majority_can_differ_from_weighted_plasmid_call(self):
        rows = self.run_consensus(
            ">p1\n" + "ACGT" * 300 + "\n",
            "seq_name\tplasmid_score\np1\t0.99\n",
            [("S1.plasme.tsv", "contig_id\tclassification\np1\tchromosome\n"),
             ("S1.platon.tsv", "contig_id\tscore\np1\t0.9\n")],
            weights="genomad:0.1,platon:0.1,plasme:0.8",
        )
        row = rows[0]
        # weighted share 0.2 < 0.5 -> chromosome, but 2/3 majority -> plasmid
        self.assertEqual(row["plasmid_call"], "chromosome")
        self.assertEqual(row["combined_prediction"], "plasmid")
        self.assertEqual(row["plasmid_count"], "2")
        self.assertEqual((self.root / "plasmids.fasta").read_text(), "")

    def test_disabled_tools_are_na_and_single_tool_majority(self):
        rows = self.run_consensus(
            ">p1\n" + "ACGT" * 300 + "\n",
            "seq_name\tplasmid_score\np1\t0.99\n",
            [],
        )
        row = rows[0]
        for tool in ("plasme", "plasx", "platon", "scapp"):
            self.assertEqual(row[tool], "NA")
        self.assertEqual(row["genomad"], "plasmid")
        self.assertEqual(row["plasmid_count"], "1")
        self.assertEqual(row["combined_prediction"], "plasmid")

    def test_consensus_header_has_ensemble_columns_in_fixed_order(self):
        rows = self.run_consensus(">p1\nACGT\n", "seq_name\tplasmid_score\np1\t0.9\n", [])
        self.assertEqual(list(rows[0].keys()),
                         ["contig_id", "sample_id", "plasmid_call", "supporting_tools",
                          "conflicting_tools", "consensus_method", "length", "gc_content",
                          "plasmid_count", "combined_prediction",
                          "genomad", "plasme", "plasx", "platon", "scapp"])


if __name__ == "__main__":
    unittest.main()
