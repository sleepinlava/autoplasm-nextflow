import csv
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "plasmid_consensus.py"
SPEC = importlib.util.spec_from_file_location("plasmid_consensus", SCRIPT)
CONSENSUS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONSENSUS)


class PlasmidConsensusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_explicit_positive_and_negative_labels_use_complete_tokens(self):
        positives = ["plasmid", "  PLASMID  ", "1", "true", "yes", "positive", "plas"]
        negatives = ["chromosome", "chromosomal", "0", "false", "no", "negative",
                     "non-plasmid", "non_plasmid", "not plasmid", " NOT__PLASMID "]
        for value in positives:
            with self.subTest(value=value):
                self.assertTrue(CONSENSUS.parse_classification(value, "plasme", "input.tsv", 2))
        for value in negatives:
            with self.subTest(value=value):
                self.assertFalse(CONSENSUS.parse_classification(value, "plasme", "input.tsv", 2))

    def test_near_matches_and_unknown_labels_fail_with_context(self):
        for value in ("10", "plasmid-like", "unknown", "unclassified", ""):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "plasme at input.tsv:7"):
                    CONSENSUS.parse_classification(value, "plasme", "input.tsv", 7)

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
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--assembly", str(assembly),
             "--genomad-summary", str(summary), "--extra", str(extra),
             "--method", "weighted_vote", "--weights", "genomad:0.1,plasme:0.9",
             "--sample-id", "S1", "--out-fasta", str(out_fasta),
             "--out-predictions", str(predictions), "--out-consensus", str(consensus)],
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(out_fasta.read_text(), "")
        with consensus.open() as fh:
            rows = list(csv.DictReader(fh, delimiter="\t"))
        self.assertEqual(rows[0]["plasmid_call"], "chromosome")

    def test_positive_only_table_contract_remains_supported(self):
        path = self.root / "sample.platon.tsv"
        path.write_text("contig_id\tscore\np1\t0.8\n")
        self.assertEqual(CONSENSUS.parse_generic_predictions(path, "platon"), {"p1": (0.8, True)})

    def test_unknown_cli_classification_fails_with_file_and_line(self):
        assembly = self.root / "assembly.fasta"
        summary = self.root / "genomad.tsv"
        extra = self.root / "S1.plasme.tsv"
        assembly.write_text(">p1\nACGT\n")
        summary.write_text("seq_name\tplasmid_score\n")
        extra.write_text("contig_id\tclassification\np1\tunknown\n")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--assembly", str(assembly),
             "--genomad-summary", str(summary), "--extra", str(extra),
             "--out-fasta", str(self.root / "out.fa"),
             "--out-predictions", str(self.root / "pred.tsv"),
             "--out-consensus", str(self.root / "cons.tsv")],
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"Unsupported classification label 'unknown' from plasme at {extra}:2", result.stderr)


if __name__ == "__main__":
    unittest.main()
