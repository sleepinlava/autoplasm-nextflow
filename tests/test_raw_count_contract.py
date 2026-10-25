"""Measured read counts must survive merging and never fall back to coverage."""
import csv
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RawCountContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def run_r(self, script, *args):
        return subprocess.run(['Rscript', str(ROOT / 'bin' / script), *map(str, args)], text=True, capture_output=True)

    def test_merge_preserves_count_independently_of_fractional_coverage(self):
        path, out = self.base / 'coverm.tsv', self.base / 'out.tsv'
        path.write_text('Contig\tA Mean\tA Read Count\np1\t0.125\t7\n')
        result = self.run_r('merge_abundance.R', '--tables', path, '--sample-ids', '001', '--out', out)
        self.assertEqual(result.returncode, 0, result.stderr)
        with out.open() as stream:
            row = next(csv.DictReader(stream, delimiter='\t'))
        self.assertEqual((row['coverage'], row['raw_count'], row['sample_id']), ('0.125', '7', '001'))

    def test_merge_rejects_invalid_count_even_when_coverage_valid(self):
        for count in ['', 'garbage', '-1', 'NaN', 'Inf', '1.5']:
            with self.subTest(count=count):
                path, out = self.base / 'coverm.tsv', self.base / 'out.tsv'
                path.write_text('Contig\tA Mean\tA Read Count\np1\t12\t' + count + '\n')
                result = self.run_r('merge_abundance.R', '--tables', path, '--sample-ids', 'S', '--out', out)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('field=raw_count', result.stderr)
                self.assertFalse(out.exists())

    def test_statistics_reject_missing_or_fractional_counts_without_coverage_proxy(self):
        metadata = self.base / 'meta.tsv'
        metadata.write_text('sample_id\tgroup\nS\tA\n')
        for script in ['network_prepare.R', 'deseq2_plasmid.R']:
            for count in [None, '', 'NA', '0.5']:
                with self.subTest(script=script, count=count):
                    path, out = self.base / 'ab.tsv', self.base / 'out.tsv'
                    header = 'sample_id\tplasmid_id\tcoverage' + ('\traw_count' if count is not None else '')
                    row = 'S\tp1\t12' + ('\t' + count if count is not None else '')
                    path.write_text(header + '\n' + row + '\n')
                    args = ['--abundance', path]
                    args += ['--out', out] if script.startswith('network') else ['--metadata', metadata, '--output', out]
                    result = self.run_r(script, *args)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('raw_count', result.stderr)
                    self.assertFalse(out.exists())

    def test_network_uses_raw_count_without_rounding_coverage(self):
        path, out = self.base / 'ab.tsv', self.base / 'out.tsv'
        path.write_text('sample_id\tplasmid_id\tcoverage\traw_count\nS1\tp1\t0.1\t7\nS2\tp1\t99.9\t9\n')
        result = self.run_r('network_prepare.R', '--abundance', path, '--out', out)
        self.assertEqual(result.returncode, 0, result.stderr)
        with out.open() as stream:
            self.assertEqual(next(csv.DictReader(stream, delimiter='\t')), {'#OTU ID': 'p1', 'S1': '7', 'S2': '9'})


if __name__ == '__main__':
    unittest.main()
