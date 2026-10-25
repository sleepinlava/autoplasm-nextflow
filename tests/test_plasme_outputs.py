"""PLASMe adapter rejects incomplete or inconsistent output pairs before writing calls."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('plasme_adapter', ROOT / 'bin/normalize_plasme_outputs.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class PlasmeOutputTests(unittest.TestCase):
    def run_case(self, change=None, error=None):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            assembly, plasmids, report, output = [p / n for n in ['assembly.fa', 'positive.fa', 'report.csv', 'calls.tsv']]
            assembly.write_text('>p1 source\nACGT\n>p2\nAAAA\n')
            plasmids.write_text('>p1 source\nACGT\n')
            header = 'contig\tlength\treference\torder\tevidence\tscore\tamb_region\n'
            report.write_text(header + 'p1\t4\treference\tBacteria\tBLASTn\tnan\t\n')
            if change:
                change(assembly, plasmids, report, header)
            if error:
                with self.assertRaisesRegex(ValueError, error):
                    adapter.normalize(assembly, plasmids, report, output)
                self.assertFalse(output.exists())
                return
            adapter.normalize(assembly, plasmids, report, output)
            return output.read_text()

    def test_blast_positive_has_explicit_call_and_retains_missing_probability(self):
        self.assertIn('p1\tplasmid\tnan\tBLASTn\treference\tBacteria\t\n', self.run_case())

    def test_header_only_negative_requires_empty_positive_fasta(self):
        result = self.run_case(lambda a, f, r, h: (f.write_text(''), r.write_text(h)))
        self.assertEqual(len(result.splitlines()), 1)

    def test_fasta_wrapping_and_sequence_whitespace_match_upstream(self):
        result = self.run_case(lambda a, f, r, h: a.write_text('>p1 description\nA C\tG\nT\n>p2\nAAAA\n'))
        self.assertIn('p1\tplasmid\tnan\tBLASTn', result)

    def test_missing_files_are_errors(self):
        for name in ['assembly', 'positive', 'report']:
            with self.subTest(name=name):
                self.run_case(lambda a, f, r, h: {'assembly': a, 'positive': f, 'report': r}[name].unlink(), 'Missing PLASMe')

    def test_bad_report_headers_are_errors(self):
        for header in ['', 'contig,score\n', 'contig\tscore\n']:
            with self.subTest(header=header):
                self.run_case(lambda a, f, r, h: r.write_text(header), 'Invalid PLASMe report header')

    def test_mismatched_identity_length_or_sequence_are_errors(self):
        cases = [lambda a, f, r, h: f.write_text('>p2\nAAAA\n'),
                 lambda a, f, r, h: f.write_text('>p1\nTGCA\n'),
                 lambda a, f, r, h: r.write_text(r.read_text().replace('p1\t4', 'p1\t99')),
                 lambda a, f, r, h: f.write_text(f.read_text() + '>p2\nAAAA\n')]
        for change in cases:
            with self.subTest(change=change):
                self.run_case(change, 'Unresolved|mismatch|IDs differ')

    def test_duplicate_ids_empty_sequences_and_broken_rows_are_errors(self):
        cases = [lambda a, f, r, h: f.write_text(f.read_text() * 2),
                 lambda a, f, r, h: f.write_text('>p1\n'),
                 lambda a, f, r, h: r.write_text(r.read_text() + r.read_text().splitlines()[1] + '\n'),
                 lambda a, f, r, h: r.write_text(h + 'p1\t4\n')]
        for change in cases:
            with self.subTest(change=change):
                self.run_case(change, 'duplicate|Duplicate|Empty|Invalid')


if __name__ == '__main__':
    unittest.main()
