import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "plasmid_catalog_prepare.R"


class CatalogPrepareTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.out = self.root / "catalog.fasta"

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *paths):
        return subprocess.run(
            ["Rscript", str(SCRIPT), "--contigs", *map(str, paths), "--out", str(self.out)],
            text=True, capture_output=True, check=False,
        )

    def fasta(self, name, content=">contig_1 description\nACGTACGT\n"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_same_contig_names_are_prefixed_by_each_sample(self):
        s1 = self.fasta("S1.plasmid_contigs.fasta")
        s2 = self.fasta("S2.plasmid_contigs.fasta")
        result = self.run_cli(s1, s2)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.out.read_text().splitlines(), [
            ">S1|contig_1", "ACGTACGT", ">S2|contig_1", "ACGTACGT",
        ])

    def test_supported_names_preserve_full_sample_id(self):
        inputs = [
            self.fasta("A__B.v1.plasmid_contigs.fasta", ">c1\nACGT\n"),
            self.fasta("S1__plasmid_contigs.fasta", ">legacy_new\nACGT\n"),
            self.fasta("A__B__plasmid_contigs.fasta", ">legacy_old\nACGT\n"),
            self.fasta("S1/plasmid_contigs.fasta", ">directory\nACGT\n"),
            self.fasta("prefix.plasmid_contigs.fasta.plasmid_contigs.fasta", ">suffix_text\nACGT\n"),
        ]
        result = self.run_cli(*inputs)
        self.assertEqual(result.returncode, 0, result.stderr)
        headers = [line for line in self.out.read_text().splitlines() if line.startswith(">")]
        self.assertEqual(set(headers), {
            ">A__B.v1|c1", ">S1|legacy_new", ">A__B|legacy_old",
            ">S1|directory", ">prefix.plasmid_contigs.fasta|suffix_text",
        })

    def test_empty_file_contributes_no_record(self):
        empty = self.fasta("S0.plasmid_contigs.fasta", "")
        good = self.fasta("S1.plasmid_contigs.fasta")
        result = self.run_cli(empty, good)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.out.read_text().splitlines(), [">S1|contig_1", "ACGTACGT"])

    def test_empty_and_invalid_sample_names_fail_without_partial_output(self):
        cases = [".plasmid_contigs.fasta", "__plasmid_contigs.fasta", "bad id.plasmid_contigs.fasta",
                 "bad|id.plasmid_contigs.fasta"]
        for name in cases:
            with self.subTest(name=name):
                self.out.unlink(missing_ok=True)
                path = self.fasta(name)
                result = self.run_cli(path)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(str(path), result.stderr)
                self.assertFalse(self.out.exists())

    def test_duplicate_header_across_input_formats_fails_and_reports_both_files(self):
        modern = self.fasta("S1.plasmid_contigs.fasta")
        legacy = self.fasta("S1__plasmid_contigs.fasta")
        result = self.run_cli(modern, legacy)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Duplicate FASTA identifier 'S1|contig_1'", result.stderr)
        self.assertIn(str(modern), result.stderr)
        self.assertIn(str(legacy), result.stderr)
        self.assertFalse(self.out.exists())

    def test_repeated_header_within_one_file_fails(self):
        path = self.fasta("S1.plasmid_contigs.fasta", ">same\nAAAA\n>same\nCCCC\n")
        result = self.run_cli(path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Duplicate FASTA identifier 'S1|same'", result.stderr)
        self.assertFalse(self.out.exists())

    def test_missing_file_empty_header_and_unsupported_name_fail(self):
        missing = self.root / "S1.plasmid_contigs.fasta"
        result = self.run_cli(missing)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(missing), result.stderr)
        self.assertFalse(self.out.exists())

        for name, content, expected in [
            ("S1.plasmid_contigs.fasta", ">\nACGT\n", "empty FASTA header"),
            ("input.fasta", ">x\nACGT\n", "Unsupported plasmid FASTA naming"),
        ]:
            with self.subTest(expected=expected):
                self.out.unlink(missing_ok=True)
                path = self.fasta(name, content)
                result = self.run_cli(path)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)
                self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
