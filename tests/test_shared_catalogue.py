"""Independent expected sequence identity, provenance and invalid-source checks."""
import csv
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('catalogue', ROOT / 'bin/build_shared_catalogue.py')
catalogue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalogue)


class SharedCatalogueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def source(self, name, text, zipped=False):
        path = self.base / name
        if zipped:
            with gzip.open(path, 'wt') as stream:
                stream.write(text)
        else:
            path.write_text(text)
        return path

    def table(self, directory, name):
        with (directory / name).open() as stream:
            return list(csv.DictReader(stream, delimiter='\t'))

    def test_different_sequences_with_same_local_id_stay_separate(self):
        a = self.source('a.fa', '>NODE_1\nAACCGT\n')
        b = self.source('b.fa', '>NODE_1\nACGATT\n')
        out = self.base / 'out'
        catalogue.build(['001', '1'], [a, b], [a, b], out)
        expected = {'seq_' + hashlib.sha256(s.encode()).hexdigest() for s in ['AACCGT', 'AATCGT']}
        self.assertEqual({r['feature_id'] for r in self.table(out, 'features.tsv')}, expected)
        self.assertEqual({r['sample_id'] for r in self.table(out, 'samples.tsv')}, {'001', '1'})

    def test_same_sequence_renamed_or_reverse_complement_collapses(self):
        a = self.source('same.fa', '>old\naaccgt\n')
        b = self.source('reverse.fa', '>new description\nACGGTT\n')
        empty = self.source('empty.fa', '')
        out = self.base / 'out'
        catalogue.build(['A', 'B'], [a, b], [a, empty], out)
        rows = self.table(out, 'features.tsv')
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['source_count'], rows[0]['plasmid_source_count'], rows[0]['is_plasmid']), ('2', '1', '1'))
        self.assertEqual([r['orientation'] for r in self.table(out, 'sources.tsv')], ['+', '-'])
        self.assertEqual(self.table(out, 'samples.tsv')[1]['status'], 'no_candidate_records')

    def test_order_and_gzip_preserve_reference_and_provenance(self):
        a = self.source('same.fa', '>old\nAACCGT\n')
        b = self.source('same.fa.GZ', '>new\nACGGTT\n', zipped=True)
        out1, out2 = self.base / 'one', self.base / 'two'
        catalogue.build(['A', 'B'], [a, b], [a, b], out1)
        catalogue.build(['B', 'A'], [b, a], [b, a], out2)
        for name in ['reference.fasta', 'features.tsv', 'sources.tsv', 'samples.tsv', 'manifest.json']:
            self.assertEqual((out1 / name).read_bytes(), (out2 / name).read_bytes())

    def test_empty_catalogue_retains_expected_sample_states(self):
        empty = self.source('empty.fa', '')
        out = self.base / 'out'
        catalogue.build(['NA', 'S2'], [empty, empty], [empty, empty], out)
        self.assertEqual((out / 'reference.fasta').read_text(), '')
        self.assertEqual(self.table(out, 'features.tsv'), [])
        self.assertEqual([r['sample_id'] for r in self.table(out, 'samples.tsv')], ['NA', 'S2'])
        self.assertTrue(all(r['status'] == 'no_assembly_records' for r in self.table(out, 'samples.tsv')))
        self.assertEqual(json.loads((out / 'manifest.json').read_text())['features'], 0)

    def test_unknown_and_changed_candidates_fail_without_partial_catalogue(self):
        a = self.source('a.fa', '>known\nAACCGT\n')
        for text in ['>absent\nAACCGT\n', '>known\nAAAAAA\n']:
            with self.subTest(text=text):
                b = self.source('bad.fa', text)
                out = self.base / 'out'
                with self.assertRaisesRegex(ValueError, 'absent|differs'):
                    catalogue.build(['S'], [a], [b], out)
                self.assertFalse(out.exists())
                self.assertEqual(list(self.base.glob('.out-*')), [])

    def test_malformed_assembly_is_not_silently_empty(self):
        for text in ['AACGT\n', '>x\n', '>x\nACGT\n>x\nACGT\n', '>x\nACZ\n', '>\nACGT\n']:
            with self.subTest(text=text):
                a = self.source('bad.fa', text)
                with self.assertRaises(ValueError):
                    catalogue.build(['S'], [a], [a], self.base / 'out')
                self.assertFalse((self.base / 'out').exists())

    def test_sample_length_duplicate_and_existing_output_guards(self):
        a = self.source('a.fa', '>x\nACGT\n')
        for ids, assemblies, plasmids in [(['S'], [], [a]), (['S', 'S'], [a, a], [a, a]), (['bad\tid'], [a], [a]), ([], [], [])]:
            with self.assertRaises(ValueError):
                catalogue.build(ids, assemblies, plasmids, self.base / 'out')
        catalogue.build(['S'], [a], [a], self.base / 'out')
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            catalogue.build(['S'], [a], [a], self.base / 'out')
        with self.assertRaisesRegex(ValueError, 'missing/unexpected'):
            catalogue.build(['S'], [a], [a], self.base / 'missing', expected_samples=2)

    def test_partial_and_ambiguous_dna_are_not_family_clusters(self):
        a = self.source('a.fa', '>full\nAACCGT\n>fragment\nAACC\n>ambiguous\nAACNGT\n')
        empty = self.source('empty.fa', '')
        out = self.base / 'out'
        catalogue.build(['S'], [a], [empty], out)
        self.assertEqual(len(self.table(out, 'features.tsv')), 3)
        self.assertTrue(all(r['is_plasmid'] == '0' for r in self.table(out, 'features.tsv')))


if __name__ == '__main__':
    unittest.main()
