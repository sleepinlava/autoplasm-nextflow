import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "coabundance_link.py"
SPECIES = "k__Bacteria|p__Example|g__Genus|s__Example"


class CoabundanceLinkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.abundance = self.root / "merged.tsv"
        self.out = self.root / "links.tsv"

    def tearDown(self):
        self.temp.cleanup()

    def write_abundance(self, values):
        with self.abundance.open("w") as fh:
            fh.write("plasmid_id\tsample_id\tcoverage\n")
            for sample, value in values:
                fh.write(f"p1\t{sample}\t{value}\n")
        return self.abundance

    def profile(self, filename, header, row, extra=""):
        path = self.root / filename
        path.write_text(extra + header + "\n" + row + "\n")
        return path

    def run_cli(self, profiles=(), sample_ids=None, *extra):
        cmd = [sys.executable, str(SCRIPT), "--plasmid-abundance", str(self.abundance),
               "--host-profiles", *map(str, profiles)]
        if sample_ids is not None:
            cmd += ["--host-sample-ids", *sample_ids]
        cmd += [*extra, "--method", "pearson", "--min-correlation", "0.5", "--out", str(self.out)]
        return subprocess.run(cmd, text=True, capture_output=True, check=False)

    def rows(self):
        with self.out.open() as fh:
            return list(csv.DictReader(fh, delimiter="\t"))

    def test_three_samples_and_multiple_metaphlan_column_layouts_correlate(self):
        self.write_abundance([("S.1", 10), ("S.2", 20), ("A__B.v1", 30)])
        profiles = [
            self.profile("profile-one.tsv",
                         "#clade_name\tNCBI_tax_id\trelative_abundance\tadditional_species",
                         f"{SPECIES}\t1\t10\t"),
            self.profile("profile-two.tsv",
                         "clade_name\trelative_abundance\tNCBI_tax_id\tadditional_species",
                         f"{SPECIES}\t20\t2\tExtra species text"),
            self.profile("profile-three.tsv",
                         "# clade_name\tadditional_species\trelative_abundance\tNCBI_tax_id",
                         f"{SPECIES}\t\t30\t3", extra="# MetaPhlAn profile\n"),
        ]
        result = self.run_cli(profiles, ["S.1", "S.2", "A__B.v1"])
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sample_id"], "A__B.v1,S.1,S.2")
        self.assertEqual(rows[0]["host_id"], SPECIES)
        self.assertAlmostEqual(float(rows[0]["score"]), 1.0, places=3)
        self.assertIn("valid host profiles: 3", result.stderr)
        self.assertIn("shared samples: 3", result.stderr)

    def test_taxonomic_child_rows_do_not_duplicate_species(self):
        self.write_abundance([("S1", 1), ("S2", 2), ("S3", 3)])
        profiles = []
        for i, (sample, abundance) in enumerate(zip(("S1", "S2", "S3"), (1, 2, 3))):
            path = self.root / f"profile-{i}.tsv"
            path.write_text(
                "clade_name\trelative_abundance\tadditional_species\n"
                f"{SPECIES}\t{abundance}\t\n"
                f"k__Bacteria|p__Example|g__Genus|s__Example|t__Strain\t{abundance}\t\n"
            )
            profiles.append(path)
        result = self.run_cli(profiles, ["S1", "S2", "S3"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([row["host_id"] for row in self.rows()], [SPECIES])

    def test_no_profiles_and_two_shared_samples_return_header_with_diagnostics(self):
        self.write_abundance([])
        result = self.run_cli([], [])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.rows(), [])
        self.assertIn("valid host profiles: 0", result.stderr)

        self.write_abundance([("S1", 10), ("S2", 20)])
        profiles = [
            self.profile(f"{sample}.metaphlan.tsv", "clade_name\trelative_abundance",
                         f"{SPECIES}\t{value}")
            for sample, value in (("S1", 10), ("S2", 20), ("S3", 30))
        ]
        result = self.run_cli(profiles, ["S1", "S2", "S3"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.rows(), [])
        self.assertIn("shared samples: 2", result.stderr)

    def test_valid_profile_without_species_still_counts_as_shared_sample(self):
        self.write_abundance([("S1", 10)])
        profile = self.root / "S1.metaphlan.tsv"
        profile.write_text("#clade_name\tNCBI_tax_id\trelative_abundance\tadditional_species\n")
        result = self.run_cli([profile], ["S1"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.rows(), [])
        self.assertIn("valid host profiles: 1", result.stderr)
        self.assertIn("shared samples: 1", result.stderr)

    def test_raw_coverm_schema_fails_with_column_context(self):
        self.abundance.write_text("Contig\tLength\tCount Mean\np1\t1000\t10\n")
        result = self.run_cli([], [])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing", result.stderr)
        self.assertIn("sample_id", result.stderr)
        self.assertIn("coverage", result.stderr)
        self.assertFalse(self.out.exists())

    def test_profile_ids_schema_numbers_and_duplicates_are_validated(self):
        self.write_abundance([("S1", 1), ("S2", 2), ("S3", 3)])
        one = self.profile("one.tsv", "clade_name\trelative_abundance", f"{SPECIES}\t1")
        result = self.run_cli([one], ["S1", "S1"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("received 2 host sample ID(s) for 1 profile(s)", result.stderr)

        bad = self.profile("bad.tsv", "clade_name\tadditional_species", f"{SPECIES}\t1")
        result = self.run_cli([bad], ["S1"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing clade_name/relative_abundance header", result.stderr)

        invalid = self.profile("invalid.tsv", "clade_name\trelative_abundance", f"{SPECIES}\tNaN")
        result = self.run_cli([invalid], ["S1"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("finite and non-negative", result.stderr)

        duplicate_profile = self.root / "duplicate-profile.tsv"
        duplicate_profile.write_text(
            "clade_name\trelative_abundance\n"
            f"{SPECIES}\t1\n{SPECIES}\t2\n"
        )
        result = self.run_cli([duplicate_profile], ["S1"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate species row", result.stderr)

        duplicate = self.root / "duplicate.tsv"
        duplicate.write_text(
            "plasmid_id\tsample_id\tcoverage\n"
            "p1\tS1\t1\n"
            "p1\tS1\t2\n"
        )
        self.abundance = duplicate
        result = self.run_cli([], [])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate ('S1', 'p1')", result.stderr)


if __name__ == "__main__":
    unittest.main()
