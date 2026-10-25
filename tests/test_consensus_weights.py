"""Configuration validation and independently specified weighted vote controls."""
from pathlib import Path
import csv
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ConsensusWeightTests(unittest.TestCase):
    def run_case(self, weights, invalid=False, method='weighted_vote'):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);assembly=p/'assembly.fa';summary=p/'genomad.tsv';platon=p/'S.platon.tsv'
            assembly.write_text('>p1\nACGT\n');summary.write_text('seq_name\tplasmid_score\n')
            platon.write_text('contig_id\np1\n')
            outputs=[p/'out.fa',p/'pred.tsv',p/'cons.tsv']
            args=['Rscript',str(ROOT/'bin/plasmid_consensus.R'),'--assembly',str(assembly),
                  '--genomad-summary',str(summary),'--extra',str(platon),'--weights='+weights,
                  '--method',method,'--out-fasta',str(outputs[0]),'--out-predictions',str(outputs[1]),'--out-consensus',str(outputs[2])]
            r=subprocess.run(args,capture_output=True,text=True)
            if invalid:
                self.assertNotEqual(r.returncode,0,f'Accepted weights {weights!r}')
                self.assertIn('Invalid consensus weights',r.stderr)
                for path in outputs:self.assertFalse(path.exists())
            else:
                self.assertEqual(r.returncode,0,r.stderr)
                with outputs[2].open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
                self.assertEqual(len(rows),1)
                return rows[0]['plasmid_call'],outputs[0].read_text()

    def test_invalid_numeric_values_rejected(self):
        for spec in ['genomad:-1','genomad:Inf','genomad:NaN','platon:garbage']:
            with self.subTest(spec=spec):self.run_case(spec,invalid=True)

    def test_malformed_items_rejected(self):
        for spec in ['genomad','genomad:1,',':1','genomad:1:2',',genomad:1','genomad:1:','genomad:']:
            with self.subTest(spec=spec):self.run_case(spec,invalid=True)

    def test_unknown_and_duplicate_keys_rejected(self):
        for spec in ['genomda:1','genomad:1,genomad:2']:
            with self.subTest(spec=spec):self.run_case(spec,invalid=True)

    def test_active_total_must_be_finite_positive(self):
        for spec in ['genomad:0,platon:0,plasme:5','genomad:1e308,platon:1e308']:
            with self.subTest(spec=spec):self.run_case(spec,invalid=True)

    def test_positive_scaling_and_missing_tool_defaults_preserved(self):
        for spec in ['genomad:0.4,platon:0.6','genomad:4,platon:6','genomad:0.4','']:
            with self.subTest(spec=spec):
                call,fasta=self.run_case(spec)
                self.assertEqual(call,'plasmid');self.assertIn('>p1',fasta)

    def test_zero_weights_do_not_block_nonweighted_method(self):
        self.run_case('genomad:0,platon:0',method='single_tool')


if __name__=='__main__':unittest.main()
