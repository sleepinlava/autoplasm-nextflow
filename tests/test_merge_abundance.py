import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "merge_abundance.R"
HEADER = "Contig\tLength\tCount Mean\tRPKM\tTPM\n"


class MergeAbundanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.out = self.root / "merged.tsv"

    def tearDown(self):
        self.temp.cleanup()

    def table(self, name, values):
        path = self.root / name
        path.write_text(HEADER + "".join(f"{feature}\t1000\t{mean}\t{rpkm}\t{tpm}\n"
                                          for feature, mean, rpkm, tpm in values))
        return path

    def run_cli(self, tables=(), sample_ids=None, extra=()):
        command = ["Rscript", str(SCRIPT), "--tables", *map(str, tables)]
        if sample_ids is not None:
            command += ["--sample-ids", *sample_ids]
        command += [*extra, "--out", str(self.out)]
        return subprocess.run(command, text=True, capture_output=True, check=False)

    def rows(self):
        with self.out.open() as fh:
            return list(csv.DictReader(fh, delimiter="\t"))

    def test_explicit_sample_ids_preserve_dots_double_underscores_and_short_suffix(self):
        tables = [
            self.table("a.coverm.tsv", [("c1", 1, 2, 3)]),
            self.table("b.coverm.tsv", [("c1", 4, 5, 6)]),
            self.table("c.coverm.tsv", [("c1", 7, 8, 9)]),
            self.table("d.coverm.tsv", [("c1", 10, 11, 12)]),
        ]
        ids = ["S.1", "S.2", "A__B.v1", "A.short"]
        result = self.run_cli(tables, ids)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([row["sample_id"] for row in self.rows()], ids)

    def test_one_three_and_zero_input_tables(self):
        one = self.table("one.tsv", [("c1", 1, 2, 3)])
        result = self.run_cli([one], ["S.1"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.rows()[0]["sample_id"], "S.1")

        two = self.table("two.tsv", [("c2", 4, 5, 6)])
        three = self.table("three.tsv", [("c3", 7, 8, 9)])
        result = self.run_cli([one, two, three], ["S.1", "S.2", "A__B.v1"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([row["sample_id"] for row in self.rows()], ["S.1", "S.2", "A__B.v1"])

        result = self.run_cli([], [])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.rows(), [])
        self.assertIn("merged 0 table(s) -> 0 rows", result.stderr)

    def test_sample_id_count_empty_and_duplicate_ids_fail(self):
        table = self.table("one.tsv", [("c1", 1, 2, 3)])
        result = self.run_cli([table], [])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--sample-ids has 0 value(s) for 1 table(s)", result.stderr)

        result = self.run_cli([table], [""])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not be empty", result.stderr)

        other = self.table("two.tsv", [("c2", 4, 5, 6)])
        result = self.run_cli([table, other], ["S1", "S1"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate sample IDs", result.stderr)

    def test_duplicate_sample_feature_fails_with_source_and_does_not_write(self):
        table = self.table("one.tsv", [("c1", 1, 2, 3), ("c1", 4, 5, 6)])
        result = self.run_cli([table], ["S1"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Duplicate ('S1', 'c1') feature", result.stderr)
        self.assertIn(str(table), result.stderr)
        self.assertFalse(self.out.exists())

    def test_legacy_filename_fallback_is_available_for_standalone_cli(self):
        table = self.table("A__B.v1.coverm.tsv", [("c1", 1, 2, 3)])
        result = self.run_cli([table])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.rows()[0]["sample_id"], "A")


if __name__ == "__main__":
    unittest.main()
