import csv
import gzip
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "sequence_similarity_link.R"
MATCHING = "ACGT" * 300


class SequenceSimilarityLinkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.plasmids = self.root / "S1.plasmid_contigs.fasta"
        self.out = self.root / "links.tsv"

    def tearDown(self):
        self.temp.cleanup()

    def fasta(self, path, records):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(f">{name}\n{seq}\n" for name, seq in records))
        return path

    def run_cli(self, *extra):
        return subprocess.run(
            ["Rscript", str(SCRIPT), "--plasmid-contigs", str(self.plasmids),
             "--sample-id", "S1", "--out", str(self.out), *map(str, extra)],
            text=True, capture_output=True, check=False,
        )

    def rows(self):
        with self.out.open() as fh:
            return list(csv.DictReader(fh, delimiter="\t"))

    def test_matching_nested_bin_links_and_taxonomy_is_attached(self):
        self.fasta(self.plasmids, [("p1", MATCHING)])
        mag_dir = self.root / "mag_bins" / "S1.metabat2_bins"
        self.fasta(mag_dir / "bin.1.fa", [("contig", MATCHING)])
        taxonomy = self.root / "taxonomy.tsv"
        taxonomy.write_text("user_genome\tclassification\nbin.1.fa\td__Bacteria;p__Example\n")
        result = self.run_cli("--host-genomes", self.root / "mag_bins" / "S1.metabat2_bins",
                              "--taxonomy", taxonomy)
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sample_id"], "S1")
        self.assertEqual(rows[0]["host_id"], "bin.1")
        self.assertAlmostEqual(float(rows[0]["score"]), 1.0, places=3)
        self.assertIn("d__Bacteria", rows[0]["supporting_data"])
        self.assertIn("valid bins: 1", result.stderr)

    def test_missing_taxonomy_uses_na(self):
        self.fasta(self.plasmids, [("p1", MATCHING)])
        mag_dir = self.root / "bins"
        self.fasta(mag_dir / "bin.1.fa", [("c1", MATCHING)])
        result = self.run_cli("--host-genomes", mag_dir)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("taxonomy=NA", self.rows()[0]["supporting_data"])

    def test_no_mag_argument_writes_header_and_reports_skip(self):
        self.fasta(self.plasmids, [("p1", MATCHING)])
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.rows(), [])
        self.assertIn("MAG path: not provided", result.stderr)
        self.assertIn("candidate FASTA files: 0; valid bins: 0; plasmids compared: 0; links: 0", result.stderr)

    def test_empty_directory_and_empty_fasta_are_valid_no_link_results(self):
        self.fasta(self.plasmids, [("p1", MATCHING)])
        empty_dir = self.root / "empty"
        empty_dir.mkdir()
        result = self.run_cli("--host-genomes", empty_dir)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.rows(), [])
        self.assertIn("candidate FASTA files: 0; valid bins: 0", result.stderr)

        empty_fasta_dir = self.root / "empty_fasta"
        empty_fasta_dir.mkdir()
        (empty_fasta_dir / "bin.1.fa").write_text("")
        result = self.run_cli("--host-genomes", empty_fasta_dir)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.rows(), [])
        self.assertIn("candidate FASTA files: 1; valid bins: 0", result.stderr)

    def test_missing_or_file_path_fails_without_normal_output(self):
        self.fasta(self.plasmids, [("p1", MATCHING)])
        missing = self.root / "missing"
        result = self.run_cli("--host-genomes", missing)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(missing), result.stderr)
        self.assertFalse(self.out.exists())

        ordinary_file = self.root / "not_a_directory"
        ordinary_file.write_text("x")
        result = self.run_cli("--host-genomes", ordinary_file)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not a directory", result.stderr)
        self.assertFalse(self.out.exists())

    def test_short_plasmid_is_skipped_but_1000_bp_record_is_compared(self):
        self.fasta(self.plasmids, [("short", MATCHING[:999]), ("long", MATCHING[:1000])])
        mag_dir = self.root / "bins"
        self.fasta(mag_dir / "bin.1.fna", [("c1", MATCHING)])
        result = self.run_cli("--host-genomes", mag_dir)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([row["plasmid_id"] for row in self.rows()], ["long"])
        self.assertIn("plasmids compared: 1", result.stderr)

    def test_fa_fna_fasta_are_read_and_fai_is_ignored(self):
        self.fasta(self.plasmids, [("p1", MATCHING)])
        mag_dir = self.root / "bins"
        for name in ("one.fa", "two.FNA", "three.fasta"):
            self.fasta(mag_dir / name, [("c1", MATCHING)])
        (mag_dir / "one.fa.fai").write_text("not fasta\n")
        (mag_dir / "ignored_dir.fa").mkdir()
        result = self.run_cli("--host-genomes", mag_dir)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("candidate FASTA files: 3", result.stderr)
        # The TETRA linker emits every bin above the threshold, not only the best.
        self.assertEqual(len(self.rows()), 3)

    def test_duplicate_host_ids_fail(self):
        self.fasta(self.plasmids, [("p1", MATCHING)])
        duplicate_dir = self.root / "duplicates"
        self.fasta(duplicate_dir / "bin.1.fa", [("c1", MATCHING)])
        self.fasta(duplicate_dir / "bin.1.fasta", [("c2", MATCHING)])
        result = self.run_cli("--host-genomes", duplicate_dir)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Duplicate MAG host_id 'bin.1'", result.stderr)
        self.assertFalse(self.out.exists())

    def test_compressed_mag_fasta_is_supported(self):
        # R file connections auto-detect gzip on read.
        self.fasta(self.plasmids, [("p1", MATCHING)])
        compressed_dir = self.root / "compressed"
        compressed_dir.mkdir()
        with gzip.open(compressed_dir / "bin.9.fa.gz", "wt") as fh:
            fh.write(">c9\n" + MATCHING + "\n")
        result = self.run_cli("--host-genomes", compressed_dir)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("valid bins: 1", result.stderr)
        self.assertEqual(self.rows()[0]["host_id"], "bin.9")

    def test_loaded_bin_with_no_similarity_is_reported_as_loaded(self):
        self.fasta(self.plasmids, [("p1", "A" * 1200)])
        mag_dir = self.root / "bins"
        self.fasta(mag_dir / "bin.1.fa", [("c1", "C" * 1200)])
        result = self.run_cli("--host-genomes", mag_dir)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.rows(), [])
        self.assertIn("valid bins: 1", result.stderr)
        self.assertIn("links: 0", result.stderr)


if __name__ == "__main__":
    unittest.main()
