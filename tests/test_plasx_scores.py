"""PlasX's official contig/score table contains both positive and negative calls."""
from pathlib import Path
import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PlasxScoreTests(unittest.TestCase):
    def run_case(self, table, error=None):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            sequences = {name: 'ACGT' * (i + 1) for i, name in enumerate(['zero', 'low', 'below', 'tie', 'above', 'high', 'one', 'missing'])}
            (base / 'assembly.fa').write_text(''.join('>' + n + '\n' + s + '\n' for n, s in sequences.items()))
            (base / 'genomad.tsv').write_text('seq_name\tplasmid_score\n')
            source = base / 'S.plasx.tsv'
            source.write_text(table)
            outputs = [base / n for n in ['out.fa', 'pred.tsv', 'cons.tsv']]
            args = ['Rscript', os.environ.get('AUTOPLASM_CONSENSUS_SCRIPT', str(ROOT / 'bin/plasmid_consensus.R')),
                    '--assembly', str(base / 'assembly.fa'), '--genomad-summary', str(base / 'genomad.tsv'),
                    '--extra', str(source), '--weights', 'genomad:0,plasx:1']
            for flag, path in zip(['--out-fasta', '--out-predictions', '--out-consensus'], outputs):
                args += [flag, str(path)]
            result = subprocess.run(args, capture_output=True, text=True)
            if os.environ.get('AUTOPLASM_SCORE_ARTIFACTS'):
                artifacts = Path(os.environ['AUTOPLASM_SCORE_ARTIFACTS'])
                artifacts.mkdir(parents=True, exist_ok=True)
                saved = Path(tempfile.mkdtemp(prefix='case-', dir=artifacts))
                shutil.copytree(base, saved, dirs_exist_ok=True)
                (saved / 'stdout.log').write_text(result.stdout)
                (saved / 'stderr.log').write_text(result.stderr)
                receipt = {'command': args, 'exit': result.returncode, 'expected_error': error,
                           'source_sha256': hashlib.sha256(Path(args[1]).read_bytes()).hexdigest(),
                           'input_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [base / 'assembly.fa', base / 'genomad.tsv', source]}}
                (saved / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n')
            if error:
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn(error, result.stderr)
                self.assertIn(str(source), result.stderr)
                self.assertTrue(all(not path.exists() for path in outputs))
                return
            self.assertEqual(result.returncode, 0, result.stderr)
            with outputs[1].open() as stream:
                predictions = list(csv.DictReader(stream, delimiter='\t'))
            with outputs[2].open() as stream:
                consensus = list(csv.DictReader(stream, delimiter='\t'))
            return outputs[0].read_text(), predictions, consensus, sequences

    def test_documented_strict_half_threshold_and_score_precision(self):
        scores = {'zero': 0, 'low': 1e-8, 'below': 0.49999999999999, 'tie': 0.5,
                  'above': 0.50000000000001, 'high': 0.99, 'one': 1}
        fasta, predictions, consensus, sequences = self.run_case('contig\tscore\n' + ''.join(n + '\t' + repr(s) + '\n' for n, s in scores.items()))
        expected = {'above', 'high', 'one'}
        self.assertEqual({r['contig_id'] for r in predictions}, set(scores))
        self.assertEqual({r['contig_id'] for r in consensus if r['plasmid_call'] == 'plasmid'}, expected)
        for row in predictions:
            self.assertEqual(float(row['plasmid_score']), scores[row['contig_id']])
            self.assertEqual(row['classification'], 'plasmid' if row['contig_id'] in expected else 'chromosome')
        self.assertEqual(fasta, ''.join('>' + n + '\n' + sequences[n] + '\n' for n in sequences if n in expected))
        self.assertTrue(all(row['plasx'] == row['plasmid_call'] for row in consensus))

    def test_invalid_probabilities_fail_before_output(self):
        for score in ['', 'bad', 'NA', 'NaN', 'Inf', '-0.1', '1.1']:
            with self.subTest(score=score):
                self.run_case('contig\tscore\nlow\t' + score + '\n', 'Invalid PlasX score')

    def test_missing_required_schema_fails_before_output(self):
        for table in ['', 'contig\nlow\n', 'contig_id\tclassification\nlow\tplasmid\n']:
            with self.subTest(table=table):
                self.run_case(table, 'PlasX predictions require contig and score columns')

    def test_duplicate_and_empty_ids_are_rejected(self):
        self.run_case('contig\tscore\nlow\t0.9\n low \t0.1\n', 'Duplicate ID')
        self.run_case('contig\tscore\n\t0.9\n', 'Empty PlasX contig ID')

    def test_header_only_is_legitimate_no_prediction(self):
        fasta, predictions, consensus, _ = self.run_case('contig\tscore\n')
        self.assertEqual((fasta, predictions, consensus), ('', [], []))


if __name__ == '__main__':
    unittest.main()
