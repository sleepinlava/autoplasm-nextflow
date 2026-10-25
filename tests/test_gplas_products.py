import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('gplas_checked', ROOT / 'bin/gplas_checked.py')
G = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(G)


class FinalGraphProducts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.graph = self.root / 'input.gfa'
        self.graph.write_text('S\t5\tACGTACGT\tKC:i:80\nS\t9\tTTGGCCAA\tKC:i:80\n')
        self.result = self.root / 'sample_results.tab'
        self.result.write_text('number Contig_name Prob_Chromosome Prob_Plasmid Prediction length coverage Bin\n'
                               '5 S5_KC:i:80_ 0 1 Plasmid 8 1 1\n'
                               '9 S9_KC:i:80_ 1 0 Repeat 8 1 1\n')
        self.members = self.root / 'sample_bins.tab'
        self.members.write_text('number Bin\n5 1\n9 1\n')
        self.fasta = self.root / 'sample_bin_1.fasta'
        self.fasta.write_text('>S5_KC:i:80_\nACGTACGT\n>S9_KC:i:80_\nTTGGCCAA\n')

    def validate(self):
        return G.validate_products(self.graph, self.root, 'sample')

    def test_membership_and_dna_consistent(self):
        state = self.validate()
        self.assertEqual((state['memberships'], state['bins']), (2, 1))

    def test_same_ids_with_foreign_dna_fail(self):
        self.fasta.write_text('>S5_KC:i:80_\nTTGGCCAA\n>S9_KC:i:80_\nACGTACGT\n')
        with self.assertRaisesRegex(ValueError, 'DNA or membership'): self.validate()

    def test_bin_membership_cannot_disagree_or_repeat(self):
        for content in ['number Bin\n5 1\n', 'number Bin\n5 1\n9 1\n9 1\n']:
            self.members.write_text(content)
            with self.assertRaisesRegex(ValueError, 'membership disagree'): self.validate()

    def test_invalid_numbers_and_identity_fail(self):
        original = self.result.read_text()
        for content in [original.replace(' 8 1 1', ' 8 NaN 1'),
                        original.replace(' 0 1 Plasmid', ' 0 1.1 Plasmid'),
                        original.replace('S5_KC:i:80_', 'S6_KC:i:80_'),
                        original.replace('Plasmid 8', 'Plasmid 7')]:
            self.result.write_text(content)
            with self.assertRaises(ValueError): self.validate()

    def test_foreign_or_partial_final_files_fail(self):
        (self.root / 'sample_bin_99.fasta').write_text('>S5_KC:i:80_\nACGTACGT\n')
        with self.assertRaisesRegex(ValueError, 'Unexpected final bin'): self.validate()

    def test_repeat_may_belong_to_multiple_bins(self):
        with self.result.open('a') as out: out.write('9 S9_KC:i:80_ 1 0 Repeat 8 1 2\n')
        with self.members.open('a') as out: out.write('9 2\n')
        (self.root / 'sample_bin_2.fasta').write_text('>S9_KC:i:80_\nTTGGCCAA\n')
        self.assertEqual(self.validate()['memberships'], 3)

    def test_isolated_candidate_is_a_native_singleton_label(self):
        self.result.write_text(self.result.read_text().replace(' 1\n', ' Isolated_1\n'))
        self.members.write_text('number Bin\n5 Isolated_1\n9 Isolated_1\n')
        self.fasta.rename(self.root / 'sample_bin_Isolated_1.fasta')
        state = self.validate()
        self.assertEqual((state['bins'], state['isolated_candidates'], state['connected_components']), (1, 1, 0))

    def test_unbinned_collection_is_not_counted_as_a_candidate_bin(self):
        self.result.write_text(self.result.read_text().replace(' 1\n', ' Unbinned\n'))
        self.members.write_text('number Bin\n5 Unbinned\n9 Unbinned\n')
        self.fasta.rename(self.root / 'sample_bin_Unbinned.fasta')
        state = self.validate()
        self.assertEqual(state['bins'], 0)
        self.assertEqual(state['unbinned_memberships'], 2)
        self.assertEqual(state['state'], 'unresolved_nodes_only')

    def test_empty_branch_column_order_matches_native_contract(self):
        self.result.write_text('Contig_name Prob_Chromosome Prob_Plasmid Prediction number length coverage Bin\n'
                               'S5_KC:i:80_ 0 1 Plasmid 5 8 1 1\n'
                               'S9_KC:i:80_ 1 0 Repeat 9 8 1 1\n')
        self.assertEqual(self.validate()['memberships'], 2)


if __name__ == '__main__':
    unittest.main()
