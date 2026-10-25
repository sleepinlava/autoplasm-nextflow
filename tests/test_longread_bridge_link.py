import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "longread_bridge_link.R"


class LongReadBridgeLinkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.plasmids = self.root / "plasmids.fasta"
        self.assembly = self.root / "assembly.fasta"
        self.sam = self.root / "alignments.sam"
        self.out = self.root / "links.tsv"
        self.plasmids.write_text(">p1\n" + "A" * 100 + "\n")
        self.assembly.write_text(">p1\n" + "A" * 100 + "\n>h1\n" + "C" * 100 + "\n")

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def record(qname, flag, target):
        return "\t".join([qname, str(flag), target, "1", "60", "100M", "*", "0", "0",
                           "A" * 100, "I" * 100]) + "\n"

    def run_cli(self, records, *extra):
        self.sam.write_text("@HD\tVN:1.6\n@SQ\tSN:p1\tLN:100\n@SQ\tSN:h1\tLN:100\n" + "".join(records))
        return subprocess.run(
            ["Rscript", str(SCRIPT), "--sam", str(self.sam),
             "--plasmid-contigs", str(self.plasmids), "--assembly", str(self.assembly),
             "--sample-id", "S1", "--out", str(self.out), *extra],
            text=True, capture_output=True, check=False,
        )

    def rows(self):
        with self.out.open() as fh:
            return list(csv.DictReader(fh, delimiter="\t"))

    def test_paired_short_reads_do_not_count_as_bridges(self):
        result = self.run_cli([
            self.record("pair/1", 0x41, "p1"),
            self.record("pair/2", 0x81, "h1"),
        ])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.rows(), [])
        self.assertIn("paired=2", result.stderr)

    def test_secondary_alignment_does_not_count_as_supplementary(self):
        result = self.run_cli([
            self.record("read1", 0, "p1"),
            self.record("read1", 0x100, "h1"),
            self.record("read2", 0, "p1"),
            self.record("read2", 0x100, "h1"),
        ])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.rows(), [])
        self.assertIn("secondary=2", result.stderr)

    def test_primary_supplementary_bridges_count_distinct_reads_only(self):
        result = self.run_cli([
            self.record("read1", 0, "p1"),
            self.record("read1", 0x800, "h1"),
            self.record("read1", 0x800, "h1"),
            self.record("read2", 0, "p1"),
            self.record("read2", 0x800, "h1"),
        ])
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["plasmid_id"], "p1")
        self.assertEqual(rows[0]["host_id"], "h1")
        self.assertEqual(rows[0]["score"], "2")
        self.assertIn("host_id_type=contig", rows[0]["supporting_data"])

    def test_single_bridge_does_not_pass_default_threshold_and_threshold_must_be_positive(self):
        result = self.run_cli([self.record("read1", 0, "p1"), self.record("read1", 0x800, "h1")])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.rows(), [])
        self.out.unlink()
        result = self.run_cli([], "--min-reads", "0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("positive integer", result.stderr)
        self.assertFalse(self.out.exists())

    def test_unmapped_qcfail_duplicate_and_supplementary_only_records_are_excluded(self):
        result = self.run_cli([
            self.record("only_supp", 0x800, "p1"),
            self.record("qcfail", 0x200, "p1"),
            self.record("duplicate", 0x400, "h1"),
            self.record("unmapped", 0x4, "*"),
        ])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.rows(), [])
        for label in ("qcfail=1", "duplicate=1", "unmapped=1"):
            self.assertIn(label, result.stderr)

    def test_bad_sam_record_fails_with_line_number_without_output(self):
        self.sam.write_text("@HD\tVN:1.6\nread1\t0\tp1\n")
        result = subprocess.run(
            ["Rscript", str(SCRIPT), "--sam", str(self.sam),
             "--plasmid-contigs", str(self.plasmids), "--assembly", str(self.assembly),
             "--out", str(self.out)], text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("alignments.sam:2", result.stderr)
        self.assertIn("fewer than 11 fields", result.stderr)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
