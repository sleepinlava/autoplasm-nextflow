"""Predeclared numeric controls; no synthetic fixture is biological calibration."""
import csv
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'bin/calibrate_sequence_threshold.py'
spec = importlib.util.spec_from_file_location('calibrate_tetra', SOURCE)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class ThresholdCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.base = Path(self.temp.name)
        self.labels = self.base / 'labels.tsv'; self.scores = self.base / 'scores.tsv'
        self.label_rows = []; self.score_rows = []
        for i, (split, label, score) in enumerate([('calibration',1,.9),('calibration',1,.8),('calibration',0,.7),('calibration',0,.1),('holdout',1,.5),('holdout',0,.9)]):
            key = dict(sample_id='S',plasmid_id=f'p{i}',host_id=f'h{i}')
            self.label_rows.append(dict(**key,label=str(label),split=split,plasmid_group=f'pg{i}',host_group=f'hg{i}',label_evidence='explicit numeric control; not biology'))
            self.score_rows.append(dict(**key,method=m.METHOD,score=str(score),profile_status='complete256'))

    def tearDown(self): self.temp.cleanup()

    def run_calibration(self):
        for path, rows in [(self.labels,self.label_rows),(self.scores,self.score_rows)]:
            with path.open('w') as f:
                w=csv.DictWriter(f,list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
        return m.calibrate([self.scores],self.labels,'recorded_assembly_host',1.)

    def test_predeclared_cutoff_and_bad_holdout_are_reported(self):
        result=self.run_calibration();self.assertEqual(result['selected_threshold'],.8)
        self.assertEqual(result['calibration']['balanced_accuracy'],1)
        self.assertEqual(result['holdout']['balanced_accuracy'],0)
        self.assertEqual((result['holdout']['fp'],result['holdout']['fn']),(1,1))

    def test_holdout_cannot_tune_cutoff(self):
        a=self.run_calibration()['selected_threshold']
        self.score_rows[-2]['score']='.99';self.score_rows[-1]['score']='-.3'
        b=self.run_calibration();self.assertEqual(a,b['selected_threshold']);self.assertEqual(b['holdout']['balanced_accuracy'],1)

    def test_host_or_plasmid_group_leakage_rejected(self):
        for key in ['host_group','plasmid_group']:
            old=self.label_rows[-1][key];self.label_rows[-1][key]=self.label_rows[0][key]
            with self.assertRaisesRegex(ValueError,'group leakage'):self.run_calibration()
            self.label_rows[-1][key]=old

    def test_missing_label_evidence_or_score_rejected(self):
        self.label_rows[0]['label_evidence']=''
        with self.assertRaisesRegex(ValueError,'label_evidence'):self.run_calibration()
        self.label_rows[0]['label_evidence']='numeric control';self.score_rows.pop()
        with self.assertRaisesRegex(ValueError,'Missing scored pair'):self.run_calibration()

    def test_wrong_method_or_nonfinite_score_rejected(self):
        self.score_rows[0]['method']='legacy_folded136'
        with self.assertRaisesRegex(ValueError,'method mismatch'):self.run_calibration()
        self.score_rows[0]['method']=m.METHOD;self.score_rows[0]['score']='nan'
        with self.assertRaisesRegex(ValueError,'Invalid Pearson'):self.run_calibration()

    def test_same_local_ids_in_distinct_samples_are_not_merged(self):
        self.label_rows[-1].update(sample_id='OTHER',plasmid_id='p0',host_id='h0')
        self.score_rows[-1].update(sample_id='OTHER',plasmid_id='p0',host_id='h0')
        result=self.run_calibration()
        self.assertEqual(result['selected_threshold'],.8)
        self.assertEqual(result['holdout']['labeled_pairs'],2)

    def test_ineligible_profile_is_abstention_not_negative(self):
        self.score_rows[-1].update(score='',profile_status='ineligible_profile')
        result=self.run_calibration()['holdout'];self.assertEqual(result['ineligible_by_label']['0'],1);self.assertEqual(result['tn'],0)
        self.assertIsNone(result['specificity'])


if __name__=='__main__':unittest.main()
