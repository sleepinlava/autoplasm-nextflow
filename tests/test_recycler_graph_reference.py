"""Independent orientation/sequence expectations; no mapper/biology claim."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import json
import hashlib

SCRIPT = Path(__file__).resolve().parents[1] / 'bin/recycler_graph_reference.py'


class GraphReferenceTests(unittest.TestCase):
    def run_case(self, graph, expected=None, diagnostic=None, provenance=None):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'graph.fastg'
            output = Path(tmp) / 'nodes.fasta'
            source.write_text(graph)
            command = [sys.executable, str(SCRIPT), '--graph', str(source), '--out', str(output)]
            if provenance is not None:
                record = {'schema': 1, 'producer': 'spades', 'version': '4.1.0',
                          'max_k': 33, 'graph_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
                record.update(provenance)
                meta = Path(tmp) / 'provenance.json'
                meta.write_text(json.dumps(record))
                command += ['--provenance', str(meta)]
            result = subprocess.run(command, capture_output=True, text=True)
            if diagnostic:
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(diagnostic, result.stderr)
                self.assertIn(str(source), result.stderr)
                self.assertFalse(output.exists())
            else:
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(output.read_text(), expected)

    def test_reverse_first_preserves_forward_bases(self):
        self.run_case(">EDGE_1';\nCGTT\n>EDGE_1;\nAACG\n", '>EDGE_1\nAACG\n')

    def test_forward_first_has_same_reference(self):
        self.run_case(">EDGE_1;\nAACG\n>EDGE_1';\nCGTT\n", '>EDGE_1\nAACG\n')

    def test_adjacency_is_not_part_of_reference_name(self):
        self.run_case(">EDGE_2:EDGE_1';\nTT\n>EDGE_1:EDGE_2;\nAA\n",
                      '>EDGE_1\nAA\n>EDGE_2\nTT\n')

    def test_reverse_only_rejected(self):
        self.run_case(">EDGE_1';\nCGTT\n", diagnostic='lacks its forward reference')

    def test_duplicate_forward_rejected_before_output(self):
        self.run_case('>EDGE_1;\nAA\n>EDGE_1;\nTT\n', diagnostic='duplicate graph node')

    def test_empty_node_rejected_before_output(self):
        self.run_case('>EDGE_1;\n', diagnostic='empty sequence')

    def test_matching_provenance(self):
        self.run_case('>EDGE_1;\nAACG\n', '>EDGE_1\nAACG\n', provenance={})

    def test_wrong_graph_provenance(self):
        self.run_case('>EDGE_1;\nAACG\n', diagnostic='SHA256 mismatch',
                      provenance={'graph_sha256': '0' * 64})

    def test_wrong_k_type_or_value(self):
        for value in [True, 33.0, '33', 0, 32]:
            with self.subTest(value=value):
                self.run_case('>EDGE_1;\nAACG\n', diagnostic='invalid graph maximum k',
                              provenance={'max_k': value})

    def test_unreviewed_producer_version(self):
        self.run_case('>EDGE_1;\nAACG\n', diagnostic='unsupported graph provenance',
                      provenance={'version': 'unreviewed'})


if __name__ == '__main__':
    unittest.main()
