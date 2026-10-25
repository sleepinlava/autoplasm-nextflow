"""Reject corrupted effective measurements before any statistical output."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class AbundanceNumericValidationTests(unittest.TestCase):
    def run_invalid(self, script, token):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);ab=base/'input.tsv';meta=base/'metadata.tsv';out=base/'out.tsv'
            meta.write_text('sample_id\tgroup\nS1\tA\n')
            field='raw_count' if script in ['network_prepare.R','deseq2_plasmid.R'] else 'coverage'
            if script=='merge_abundance.R':
                ab.write_text('Contig\tS1 Mean\np1\t'+token+'\n')
                args=['--tables',str(ab),'--sample-ids','S1','--out',str(out)]
            else:
                cid='plasmid_id' if script in ['network_prepare.R','deseq2_plasmid.R'] else 'contig_id'
                # Coverage is also invalid when counts are absent: no invented zero/fallback.
                ab.write_text(f'sample_id\t{cid}\traw_count\tcoverage\nS1\tp1\t{token}\t{token}\n')
                args=['--abundance',str(ab)]
                if script=='diversity.R':args+=['--metadata',str(meta),'--out-metrics',str(out),'--out-beta',str(base/'beta.tsv')]
                elif script=='differential_abundance.R':args+=['--metadata',str(meta),'--out',str(out)]
                elif script=='deseq2_plasmid.R':args+=['--metadata',str(meta),'--output',str(out)]
                else:args+=['--out',str(out)]
            r=subprocess.run(['Rscript',str(ROOT/'bin'/script),*args],capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0,f'{script} accepted {token!r}')
            self.assertIn('Invalid numeric value',r.stderr)
            self.assertIn(str(ab),r.stderr)
            self.assertIn('S1',r.stderr);self.assertIn('p1',r.stderr)
            self.assertFalse(out.exists())
            self.assertFalse((base/'beta.tsv').exists())

    def check_script(self,script):
        tokens=['garbage'] if os.environ.get('AUTOPLASM_NUMERIC_RED') else ['garbage','NA','','NaN','Inf','-1']
        for token in tokens:
            with self.subTest(script=script,token=token):self.run_invalid(script,token)

    def test_diversity_rejects_invalid_measurements(self):self.check_script('diversity.R')
    def test_differential_rejects_invalid_measurements(self):self.check_script('differential_abundance.R')
    def test_network_rejects_invalid_effective_values(self):self.check_script('network_prepare.R')
    def test_deseq_rejects_invalid_effective_values(self):self.check_script('deseq2_plasmid.R')
    def test_merge_rejects_invalid_coverage(self):self.check_script('merge_abundance.R')

    def test_missing_numeric_schema_is_not_empty_biology(self):
        for script in ['diversity.R','differential_abundance.R','network_prepare.R',
                       'deseq2_plasmid.R','merge_abundance.R']:
            with self.subTest(script=script), tempfile.TemporaryDirectory() as directory:
                base=Path(directory);ab=base/'input.tsv';meta=base/'meta.tsv';out=base/'out.tsv'
                meta.write_text('sample_id\tgroup\nS1\tA\n')
                ab.write_text('Contig\n' if script=='merge_abundance.R' else
                              'sample_id\tcontig_id\tplasmid_id\n')
                if script=='merge_abundance.R':args=['--tables',str(ab),'--sample-ids','S1','--out',str(out)]
                else:
                    args=['--abundance',str(ab)]
                    if script=='diversity.R':args+=['--metadata',str(meta),'--out-metrics',str(out),'--out-beta',str(base/'beta.tsv')]
                    elif script=='differential_abundance.R':args+=['--metadata',str(meta),'--out',str(out)]
                    elif script=='deseq2_plasmid.R':args+=['--metadata',str(meta),'--output',str(out)]
                    else:args+=['--out',str(out)]
                r=subprocess.run(['Rscript',str(ROOT/'bin'/script),*args],capture_output=True,text=True)
                self.assertNotEqual(r.returncode,0)
                self.assertIn('missing',r.stderr.lower());self.assertIn(str(ab),r.stderr)
                self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()
