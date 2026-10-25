"""Shared reference table completeness, count units and failure propagation."""
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('shared_abundance', ROOT / 'bin/collect_shared_abundance.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SharedAbundanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.catalogue = self.base / 'catalogue'
        self.catalogue.mkdir()
        (self.catalogue / 'features.tsv').write_text('feature_id\tis_plasmid\nF1\t1\nF2\t0\n')
        (self.catalogue / 'samples.tsv').write_text('sample_id\n001\n1\n')
        self.out = self.base / 'out'

    def tearDown(self):
        self.temp.cleanup()

    def coverm(self, name, count='7', second='0', extra=''):
        path = self.base / name
        path.write_text('Contig\tinput Mean\tinput RPKM\tinput TPM\tinput Read Count' + extra + '\n'
                        + 'F1\t0.125\t400\t1000000\t' + count + '\nF2\t0\t0\t0\t' + second + '\n')
        return path

    def read(self, name):
        with (self.out / name).open() as stream:
            return list(csv.DictReader(stream, delimiter='\t'))

    def test_counts_are_not_rounded_coverage_and_samples_remain_distinct(self):
        a, b = self.coverm('a.tsv'), self.coverm('b.tsv', count='0')
        module.collect(self.catalogue, ['1', '001'], [b, a], 'bowtie2', self.out)
        rows = self.read('contig_abundance.tsv')
        self.assertEqual([(r['sample_id'], r['contig_id'], r['raw_count']) for r in rows], [('001', 'F1', '7'), ('001', 'F2', '0'), ('1', 'F1', '0'), ('1', 'F2', '0')])
        self.assertEqual([r['plasmid_id'] for r in self.read('plasmid_abundance.tsv')], ['F1', 'F1'])
        self.assertTrue(all(r['count_unit'] == 'primary_read_alignment' for r in rows))
        self.assertEqual(self.read('sample_states.tsv')[1]['quantification_status'], 'measured_zero')
        self.assertIn('not fragment counts', json.loads((self.out / 'method.json').read_text())['paired_end'])

    def test_missing_or_duplicate_sample_is_an_error_not_zero(self):
        a = self.coverm('a.tsv')
        for ids, tables in [(['001'], [a]), (['001', '001'], [a, a]), (['001', 'extra'], [a, a]), (['001', '1'], [a]), ([], [])]:
            with self.subTest(ids=ids):
                with self.assertRaises(ValueError):
                    module.collect(self.catalogue, ids, tables, 'bowtie2', self.out)
                self.assertFalse(self.out.exists())

    def test_invalid_counts_are_not_replaced_by_coverage(self):
        for value in ['0.4', '-1', 'NaN', 'Inf', '', 'NA', 'broken']:
            with self.subTest(value=value):
                a = self.coverm('a.tsv', count=value)
                with self.assertRaises(ValueError):
                    module.collect(self.catalogue, ['001', '1'], [a, a], 'bowtie2', self.out)
                self.assertFalse(self.out.exists())
                self.assertFalse(list(self.base.glob('.out-*')))

    def test_missing_or_ambiguous_count_columns_fail(self):
        a = self.coverm('a.tsv')
        for header in ['input Other', 'input Read Count\tsecond Read Count']:
            a.write_text(a.read_text().replace('input Read Count', header))
            with self.assertRaises(ValueError):
                module.collect(self.catalogue, ['001', '1'], [a, a], 'bowtie2', self.out)
            a = self.coverm('a.tsv')

    def test_missing_extra_duplicate_and_unknown_features_fail(self):
        for change in ['missing', 'extra', 'duplicate', 'renamed']:
            with self.subTest(change=change):
                a = self.coverm('a.tsv')
                lines = a.read_text().splitlines(True)
                if change == 'missing':
                    lines = lines[:-1]
                elif change == 'extra':
                    lines.append('F3\t0\t0\t0\t0\n')
                elif change == 'duplicate':
                    lines.append(lines[-1])
                else:
                    lines[1] = lines[1].replace('F1', 'unknown')
                a.write_text(''.join(lines))
                with self.assertRaises(ValueError):
                    module.collect(self.catalogue, ['001', '1'], [a, a], 'bowtie2', self.out)
                self.assertFalse(self.out.exists())

    def test_invalid_noncount_metrics_fail_before_publish(self):
        for value in ['NaN', '-0.1', 'garbage', '']:
            a = self.coverm('a.tsv')
            a.write_text(a.read_text().replace('0.125', value))
            with self.assertRaises(ValueError):
                module.collect(self.catalogue, ['001', '1'], [a, a], 'bowtie2', self.out)
            self.assertFalse(self.out.exists())

    def test_globally_empty_catalogue_records_all_expected_samples(self):
        (self.catalogue / 'features.tsv').write_text('feature_id\tis_plasmid\n')
        module.collect(self.catalogue, [], [], 'minimap2', self.out)
        self.assertEqual(self.read('contig_abundance.tsv'), [])
        self.assertEqual(self.read('plasmid_abundance.tsv'), [])
        states = self.read('sample_states.tsv')
        self.assertEqual([r['sample_id'] for r in states], ['001', '1'])
        self.assertTrue(all(r['quantification_status'] == 'empty_catalogue' for r in states))


if __name__ == '__main__':
    unittest.main()
