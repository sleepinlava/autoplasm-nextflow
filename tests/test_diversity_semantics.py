"""Independent alpha/Bray formula checks, including shape and legitimate zeros."""
import csv,json,math,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'bin/diversity.R'


class DiversitySemanticsTests(unittest.TestCase):
    def run_case(self, values, norm='none'):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory);ids=['001','1','NA'][:len(values)];features=len(values[0]);ab=d/'ab.tsv';ab.write_text('sample_id\tcontig_id\tcoverage\n'+''.join(f'{sid}\tF{j}\t{v}\n' for sid,row in zip(ids,values) for j,v in enumerate(row)));meta=d/'meta.tsv';meta.write_text('sample_id\tgroup\n'+''.join(s+'\tG\n' for s in ids));cmd=['Rscript',str(SCRIPT),'--abundance',str(ab),'--metadata',str(meta),'--out-metrics',str(d/'alpha.tsv'),'--out-beta',str(d/'beta.tsv'),'--out-status',str(d/'status.json'),'--beta-normalization',norm];r=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
            with (d/'alpha.tsv').open() as f:alpha=list(csv.DictReader(f,delimiter='\t'))
            with (d/'beta.tsv').open() as f:beta=list(csv.DictReader(f,delimiter='\t'))
            self.assertEqual(len(alpha),4*len(ids));self.assertEqual({x['sample_id'] for x in alpha},set(ids));self.assertEqual({x['sample_id'] for x in beta},set(ids))
            for sid,row in zip(ids,values):
                total=sum(row);p=[v/total for v in row if v>0] if total else [];rich=len(p);h=-sum(x*math.log(x) for x in p);simpson=1-sum(x*x for x in p) if p else 0;expected={'richness':rich,'shannon':h,'simpson':simpson,'pielou':h/math.log(rich) if rich>1 else 0}
                actual={x['metric']:float(x['value']) for x in alpha if x['sample_id']==sid}
                for key,value in expected.items():self.assertTrue(math.isfinite(actual[key]));self.assertAlmostEqual(actual[key],value,places=6)
            adjusted=[[v/sum(row) for v in row] if norm=='tss' and sum(row) else row for row in values]
            for row in beta:
                i=ids.index(row['sample_id'])
                for j,sid in enumerate(ids):
                    den=sum(adjusted[i])+sum(adjusted[j]);expected=sum(abs(a-b) for a,b in zip(adjusted[i],adjusted[j]))/den if den else 0
                    self.assertAlmostEqual(float(row[sid]),expected,places=6)
            return json.loads((d/'status.json').read_text())

    def test_single_feature_multiple_samples_including_zero(self):self.run_case([[0],[2],[5]])
    def test_single_feature_tss(self):self.run_case([[0],[2],[5]],'tss')
    def test_single_sample(self):self.assertEqual(self.run_case([[3,1]])["sample_ids"],["001"])
    def test_multiple_features_independent_values(self):self.run_case([[1,1],[3,1],[0,0]])
    def test_multiple_features_tss(self):self.run_case([[1,1],[3,1],[0,0]],'tss')
    def test_zero_features_preserves_full_metadata_cohort(self):
        self.assertEqual(self.run_case([[],[],[]])['status'],'zero_feature_input')
    def test_zero_measurements_are_finite_and_declared(self):
        self.assertEqual(self.run_case([[0,0],[0,0]])['status'],'measured_all_zero')


if __name__=='__main__':unittest.main()
