"""Final network matrix invariants; preparation is distinct from inference."""
import csv,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


class NetworkEligibilityTests(unittest.TestCase):
    def invoke(self, values, minimum=20):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory);ids=['S'+str(i) for i in range(20)];ab=d/'ab.tsv';ab.write_text('sample_id\tplasmid_id\traw_count\tcoverage\n'+''.join(f'{s}\tF{j}\t{v}\t0.125\n' for j,row in enumerate(values) for s,v in zip(ids,row)));meta=d/'meta.tsv';meta.write_text('sample_id\tgroup\n'+''.join(s+'\tA\n' for s in ids));cmd=['Rscript',str(ROOT/'bin/network_prepare.R'),'--abundance',str(ab),'--metadata',str(meta),'--min-samples',str(minimum),'--out',str(d/'matrix.tsv'),'--out-status',str(d/'status.json'),'--eligible-out',str(d/'eligible.tsv')];r=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);status=json.loads((d/'status.json').read_text())
            with (d/'matrix.tsv').open() as f:reader=csv.DictReader(f,delimiter='\t');fields=reader.fieldnames;rows=list(reader)
            self.assertEqual((d/'eligible.tsv').exists(),status['eligible'])
            if rows:
                for sid in fields[1:]:self.assertGreater(sum(int(row[sid]) for row in rows),0)
            if status['eligible']:self.assertEqual((d/'matrix.tsv').read_bytes(),(d/'eligible.tsv').read_bytes())
            return status,rows,fields
    def test_positive_final_matrix_is_eligible(self):
        status,rows,fields=self.invoke([[100+i+j*3 for i in range(20)] for j in range(4)]);self.assertTrue(status['eligible']);self.assertEqual(len(rows),4);self.assertEqual(len(fields),21)
    def test_new_zero_columns_after_prevalence_are_removed(self):
        common=[[10+j if i<4 else 0 for i in range(20)] for j in range(4)];rare=[[5 if i==j else 0 for i in range(20)] for j in range(4,20)];status,rows,fields=self.invoke(common+rare);self.assertEqual(status['reason'],'insufficient_samples');self.assertEqual(len(fields),5);self.assertEqual(len(status['excluded_zero_after_prevalence']),16);self.assertEqual(status['prevalence_denominator'],20)
    def test_every_feature_filtered_produces_no_eligible_file(self):
        status,rows,fields=self.invoke([[3 if i==j else 0 for i in range(20)] for j in range(20)]);self.assertEqual(status['reason'],'insufficient_features');self.assertEqual(rows,[]);self.assertEqual(fields,['#OTU ID'])
    def test_fast_spar_requires_four_components(self):
        status,rows,_=self.invoke([[5+i+j for i in range(20)] for j in range(3)]);self.assertEqual(status['min_features'],4);self.assertFalse(status['eligible']);self.assertEqual(len(rows),3)
    def test_all_measured_zero_is_not_an_inference(self):
        status,rows,_=self.invoke([[0]*20 for _ in range(4)]);self.assertFalse(status['eligible']);self.assertEqual(len(status['excluded_initial_zero']),20);self.assertEqual(rows,[])
    def test_global_empty_keeps_expected_cohort_in_status(self):
        status,rows,_=self.invoke([]);self.assertFalse(status['eligible']);self.assertEqual(len(status['observed_or_expected_sample_ids']),20);self.assertEqual(rows,[])
    def test_single_included_id_is_an_array_and_does_not_meet_cohort_gate(self):
        status,rows,fields=self.invoke([[5+j if i==0 else 0 for i in range(20)] for j in range(4)])
        self.assertEqual(status['included_sample_ids'],['S0']);self.assertEqual(status['reason'],'insufficient_samples')
    def test_counts_above_R_integer_range_are_not_coerced_to_NA(self):
        count=2**31+123;status,rows,_=self.invoke([[count+i+j for i in range(20)] for j in range(4)]);self.assertTrue(status['eligible']);self.assertEqual(rows[0]['S0'],str(count));self.assertFalse(any('NA'==v for row in rows for v in row.values()))

    def test_invalid_minimum_samples_rejects_before_reading_data(self):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory)
            for value in ['0','1','1.5','NaN','Inf','bad']:
                with self.subTest(value=value):
                    result=subprocess.run(['Rscript',str(ROOT/'bin/network_prepare.R'),
                        '--abundance',str(d/'not_read.tsv'),'--min-samples',value,
                        '--out',str(d/'out.tsv')],capture_output=True,text=True)
                    self.assertNotEqual(result.returncode,0)
                    self.assertIn('--min-samples',result.stderr)
                    self.assertFalse((d/'out.tsv').exists())


if __name__=='__main__':unittest.main()
