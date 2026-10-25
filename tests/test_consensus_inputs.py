"""Consensus inputs share the assembly ID universe; retired SCAPP inputs fail."""
from pathlib import Path
import csv
import gzip
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ConsensusInputTests(unittest.TestCase):
    def run_case(self, assembly='>p1\nACGT\n', summary='seq_name\tplasmid_score\np1\t0.99\n',
                 extra=None, weights=None, error=None, include_all=None, method=None):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / 'assembly.fa').write_text(assembly)
            (base / 'genomad.tsv').write_text(summary)
            outputs = [base / name for name in ['out.fa', 'pred.tsv', 'cons.tsv']]
            args = ['Rscript', str(ROOT / 'bin/plasmid_consensus.R'),
                    '--assembly', str(base / 'assembly.fa'),
                    '--genomad-summary', str(base / 'genomad.tsv')]
            if extra:
                name, content = extra
                path = base / name
                if name.endswith('.gz'):
                    with gzip.open(path, 'wt') as stream:
                        stream.write(content)
                else:
                    path.write_text(content)
                args += ['--extra', str(path)]
            if weights is not None:
                args += ['--weights', weights]
            if include_all is not None:
                args += ['--include-all-contigs', include_all]
            if method is not None:
                args += ['--method', method]
            for flag, path in zip(['--out-fasta', '--out-predictions', '--out-consensus'], outputs):
                args += [flag, str(path)]
            result = subprocess.run(args, capture_output=True, text=True)
            if error:
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn(error, result.stderr)
                self.assertTrue(all(not path.exists() for path in outputs))
                return
            self.assertEqual(result.returncode, 0, result.stderr)
            with outputs[2].open() as stream:
                reader = csv.DictReader(stream, delimiter='\t')
                rows = list(reader)
                self.assertEqual(reader.fieldnames[-4:], ['genomad', 'plasme', 'plasx', 'platon'])
                self.assertNotIn('scapp', reader.fieldnames)
            return outputs[0].read_text(), rows

    def test_retired_fasta_sources_rejected_before_output(self):
        for name in ['S.scapp.fasta', 'S.scapp.fa.gz', 'confident_cycs.fasta',
                     'S.confident_cycs.fna.gz']:
            with self.subTest(name=name):
                self.run_case(extra=(name, '>RNODE_1\nACGT\n'),
                              error='SCAPP support has been removed; unsupported prediction source:')

    def test_retired_weight_rejected_before_output(self):
        self.run_case(weights='genomad:0.6,scapp:0.4',
                      error='SCAPP support has been removed; remove scapp from consensus weights')

    def test_unknown_prediction_ids_rejected_even_for_negative_calls(self):
        for label in ['plasmid', 'chromosome']:
            with self.subTest(label=label):
                self.run_case(extra=('S.platon.tsv', 'contig_id\tclassification\nmissing\t' + label + '\n'),
                              error="Unresolved prediction ID 'missing' from platon")
        self.run_case(summary='seq_name\tplasmid_score\nmissing\t0.99\n',
                      error="Unresolved prediction ID 'missing' from genomad")

    def test_empty_record_rejected_before_output(self):
        self.run_case(assembly='>p1\n\n>p2\nACGT\n', error="Empty FASTA sequence 'p1'")

    def test_empty_assembly_and_empty_predictions_remain_valid(self):
        fasta, rows = self.run_case(assembly='', summary='seq_name\tplasmid_score\n')
        self.assertEqual(fasta, '')
        self.assertEqual(rows, [])

    def test_remaining_tool_with_scapp_in_sample_name_is_valid(self):
        fasta, rows = self.run_case(extra=('sample.scapp.confident_cycs.platon.tsv',
                                          'contig_id\tclassification\np1\tplasmid\n'))
        self.assertEqual(fasta, '>p1\nACGT\n')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['plasmid_call'], 'plasmid')
        self.assertEqual(rows[0]['platon'], 'plasmid')
        self.assertEqual(rows[0]['length'], '4')
        self.assertEqual(rows[0]['gc_content'], '0.5000')

    def test_graph_domain_applies_same_vote_to_unreported_nodes(self):
        for method in ['intersection', 'majority_vote', 'weighted_vote', 'single_tool']:
            with self.subTest(method=method):
                kwargs = dict(assembly='>p1\nACGT\n>p2\nTTGCAA\n', method=method)
                original_fasta, original_rows = self.run_case(**kwargs)
                graph_fasta, graph_rows = self.run_case(**kwargs, include_all='true')
                self.assertEqual(graph_fasta, original_fasta)
                self.assertEqual(graph_rows[0], original_rows[0])
                self.assertEqual(graph_rows[1]['contig_id'], 'p2')
                self.assertEqual(graph_rows[1]['plasmid_call'], 'chromosome')
                self.assertEqual(graph_rows[1]['plasmid_count'], '0')
                self.assertEqual(graph_rows[1]['supporting_tools'], '')
                self.assertEqual(graph_rows[1]['genomad'], 'chromosome')
                self.assertEqual(graph_rows[1]['plasx'], 'NA')

    def test_invalid_graph_domain_option_fails_before_outputs(self):
        self.run_case(include_all='unassessed', error='--include-all-contigs must be true or false')


if __name__ == '__main__':
    unittest.main()
