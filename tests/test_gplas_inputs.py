import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('gplas_inputs', ROOT / 'bin/gplas_inputs.py')
G = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(G)


class GraphNodeInputs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.graph = self.root / 'assembly.gfa'
        self.graph.write_text('H\tVN:Z:1.0\nS\t5\t' + 'ACGT' * 250 +
                              '\tDP:f:225.865\tKC:i:218411\nS\t9\t' + 'TGCA' * 249 +
                              '\tDP:f:2\tKC:i:300\nL\t5\t+\t9\t-\t33M\n')

    def prepare(self):
        return G.prepare(self.graph, self.root / 'sample', 'A.1')

    def consensus(self, **changes):
        row = dict(contig_id='S5_KC:i:218411_', sample_id='internal_nodes_A',
                   plasmid_call='plasmid', length='1000')
        row.update(changes)
        path = self.root / 'consensus.tsv'
        with path.open('w', newline='') as out:
            writer = csv.DictWriter(out, fieldnames=list(row), delimiter='\t')
            writer.writeheader(); writer.writerow(row)
        return path

    def predict(self, table):
        assessment = self.root / 'assessment.tsv'
        if not assessment.exists():
            assessment.write_text('seq_name\tchromosome_score\tplasmid_score\tvirus_score\nS5_KC:i:218411_\t0.1\t0.8\t0.1\n')
        return G.predictions(self.root / 'sample.gplas.gfa', table,
                             self.root / 'prediction.tab', 'A.1', 'internal_nodes_A', assessment)

    def test_missing_assessment_is_not_encoded_as_a_negative(self):
        self.prepare()
        path = self.root / 'assessment.tsv'
        path.write_text('seq_name\tchromosome_score\tplasmid_score\tvirus_score\n')
        with self.assertRaisesRegex(ValueError, 'not all assessed'):
            self.predict(self.consensus())
        self.assertFalse((self.root / 'prediction.tab').exists())

    def test_node_dna_and_native_awk_identity_preserved(self):
        state = self.prepare()
        graph = self.root / 'sample.gplas.gfa'
        # Independent fixed-upstream extraction expression. Assembly contig IDs
        # are deliberately absent; output must be the GFA segment DNA and header.
        awk = subprocess.check_output(['awk', r'{if($1 == "S") print ">"$1$2"_"$4"_"$5"\n"$3}', str(graph)], text=True)
        native_first = '\n'.join(awk.splitlines()[:2]) + '\n'
        self.assertEqual((self.root / 'sample.gplas_nodes.fasta').read_text(), native_first)
        self.assertIn('>S5_KC:i:218411_\n' + 'ACGT' * 250, native_first)
        self.assertEqual((state['total_nodes'], state['classified_nodes'], state['links']), (2, 1, 1))
        self.assertEqual(state['nodes'][0]['original_tags'], ['DP:f:225.865', 'KC:i:218411'])
        self.assertIn('L\t5\t+\t9\t-\t33M', graph.read_text())

    def test_binary_decisions_have_explicit_interpretation(self):
        self.prepare(); state = self.predict(self.consensus())
        with (self.root / 'prediction.tab').open() as stream:
            rows = list(csv.reader(stream, delimiter='\t'))
        self.assertEqual(rows, [G.HEADER, ['0', '1', 'Plasmid', 'S5_KC:i:218411_', '1000']])
        self.assertEqual((state['plasmid_seeds'], state['not_assessed_length_filter']), (1, 1))
        self.assertIn('not calibrated', state['encoding'])

    def test_no_seeds_is_distinct_from_unassessed(self):
        self.prepare(); state = self.predict(self.consensus(plasmid_call='chromosome'))
        self.assertEqual(state['state'], 'no_plasmid_seeds')
        self.assertEqual(state['classified_nodes'], 1)

    def test_small_nodes_are_unassessed(self):
        self.graph.write_text('S\t3\tACGT\tKC:i:8\n')
        state = self.prepare()
        self.assertEqual(state['state'], 'not_assessed_length_filter')
        self.assertEqual((self.root / 'sample.gplas_nodes.fasta').read_bytes(), b'')

    def test_foreign_or_unassessed_consensus_is_rejected(self):
        self.prepare()
        for change in [dict(contig_id='NODE_5_length_1000_cov_225.865'),
                       dict(sample_id='another_sample'), dict(length='999'),
                       dict(plasmid_call='unassessed')]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.predict(self.consensus(**change))
            self.assertFalse((self.root / 'prediction.tab').exists())

    def test_missing_or_duplicate_classification_is_rejected(self):
        self.prepare(); table = self.consensus()
        contents = table.read_text()
        for bad in [contents.splitlines()[0] + '\n', contents + contents.splitlines()[1] + '\n']:
            table.write_text(bad)
            with self.assertRaises(ValueError): self.predict(table)

    def test_invalid_graphs_fail_before_products(self):
        original = self.graph.read_text()
        for text in [original.replace('KC:i:218411', 'KC:i:-1'),
                     original.replace('DP:f:225.865', 'DP:f:NaN'),
                     original.replace('L\t5\t+', 'L\t100\t+'),
                     original + 'S\t5\tACGT\tKC:i:4\n',
                     original + 'J\t5\t+\t9\t-\t100\n',
                     original.replace('\tDP:f:225.865', '\tLN:i:999'),
                     'S\t1\t*\tKC:i:1\n', 'S\t1\tACGT\tKC:i:0\n']:
            with self.subTest(text=text[:70]):
                self.graph.write_text(text)
                with self.assertRaises(ValueError): self.prepare()
                self.assertFalse((self.root / 'sample.gplas.gfa').exists())

    def test_existing_products_are_never_reused_as_new_success(self):
        self.prepare()
        with self.assertRaises(ValueError): self.prepare()
        self.predict(self.consensus())
        with self.assertRaises(ValueError): self.predict(self.consensus())


if __name__ == '__main__':
    unittest.main()
