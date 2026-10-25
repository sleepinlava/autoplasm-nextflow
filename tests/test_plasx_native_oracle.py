"""Counterfactuals for independent PlasX model arithmetic and score domains."""
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('plasx_native_oracle', Path(__file__).with_name('run_plasx_native.py'))
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)


class NativeOracleTests(unittest.TestCase):
    def test_repeated_families_and_multi_accessions_are_counts_not_presence(self):
        genes = [{'gene_callers_id': '1', 'contig': 'internal'}, {'gene_callers_id': '2', 'contig': 'internal'}]
        annotations = [[{'gene_callers_id': '1', 'accession': 'COG1!!!PF1.2'},
                        {'gene_callers_id': '2', 'accession': 'COG1'}],
                       [{'gene_callers_id': '1', 'contig': 'internal', 'accession': 'mmseqs_5_7'}]]
        counts = oracle.families(genes, annotations, {'internal': 'original'})
        self.assertEqual(counts, {'original': {'COG1': 2, 'PF1.2': 1, 'mmseqs_5_7': 1}})
        with tempfile.TemporaryDirectory() as temp:
            model = Path(temp) / 'model.tsv'
            model.write_text('accession\tPlasX_coefficient\nINTERCEPT\t-1\nCOG1\t2\nPF1.2\t-3\nmmseqs_5_7\t1\n')
            observed = oracle.probabilities(counts, model)['original']
            self.assertAlmostEqual(observed, 1 / (1 + math.exp(-1)))
            self.assertNotAlmostEqual(observed, 1 / (1 + math.exp(1)))  # incorrect binary features

    def test_foreign_annotation_and_duplicate_gene_ids_are_rejected(self):
        gene = {'gene_callers_id': '1', 'contig': 'A'}
        with self.assertRaisesRegex(AssertionError, 'Foreign annotation'):
            oracle.families([gene], [[{'gene_callers_id': '1', 'contig': 'B', 'accession': 'COG1'}]])
        with self.assertRaisesRegex(AssertionError, 'Duplicate gene'):
            oracle.families([gene, gene], [])

    def test_missing_score_or_added_unassessed_score_is_not_a_pass(self):
        for observed in [{}, {'A': .8, 'unassessed': 0}]:
            with self.subTest(observed=observed), self.assertRaisesRegex(AssertionError, 'domain'):
                oracle.compare_scores({'A': .8}, observed)

    def test_changed_score_and_nonfinite_score_are_rejected(self):
        for observed in [.7, float('nan'), float('inf'), -1, 2]:
            with self.subTest(observed=observed), self.assertRaises(AssertionError):
                oracle.compare_scores({'A': .8}, {'A': observed})

    def test_empty_annotation_domain_does_not_manufacture_intercept_scores(self):
        with tempfile.TemporaryDirectory() as temp:
            model = Path(temp) / 'model.tsv'
            model.write_text('accession\tPlasX_coefficient\nINTERCEPT\t-1\n')
            self.assertEqual(oracle.probabilities({}, model), {})
            self.assertEqual(oracle.compare_scores({}, {}), 0)


if __name__ == '__main__':
    unittest.main()
