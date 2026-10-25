"""Producer-state evidence distinguishes an empty reference from missing results."""
import csv,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'bin'))
from validate_statistics_inputs import validate


class StatisticsInputValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.ids=['001','1','NA'];self.contigs=self.base/'contigs.tsv';self.plasmids=self.base/'plasmids.tsv';self.states=self.base/'states.tsv';self.metadata=self.base/'meta.tsv';self.out=self.base/'validated';self.values={'F1':[2,0,5],'F2':[3,0,4]};self.crows=[];self.prows=[];self.srows=[]
        for j,sid in enumerate(self.ids):
            for fid,v in self.values.items():
                row={'contig_id':fid,'sample_id':sid,'coverage':str(v[j]/10),'raw_count':str(v[j])};self.crows.append(row)
                if fid=='F1':self.prows.append(dict(plasmid_id=fid,**{k:x for k,x in row.items() if k!='contig_id'}))
            total=sum(v[j] for v in self.values.values());self.srows.append(dict(sample_id=sid,reference_features=2,plasmid_features=1,eligible_read_alignments=total,plasmid_read_alignments=self.values['F1'][j],quantification_status='measured' if total else 'measured_zero'))
        self.metadata.write_text('sample_id\tgroup\n'+''.join(s+'\tG\n' for s in self.ids))
    def tearDown(self):self.temp.cleanup()
    def table(self,path,rows,fields):
        with path.open('w') as f:w=csv.DictWriter(f,fields,delimiter='\t');w.writeheader();w.writerows(rows)
    def invoke(self):
        self.table(self.contigs,self.crows,['contig_id','sample_id','coverage','raw_count']);self.table(self.plasmids,self.prows,['plasmid_id','sample_id','coverage','raw_count']);self.table(self.states,self.srows,['sample_id','reference_features','plasmid_features','eligible_read_alignments','plasmid_read_alignments','quantification_status']);validate(self.contigs,self.plasmids,self.states,self.metadata,3,self.out)
    def rejected(self,text):
        with self.assertRaisesRegex(ValueError,text):self.invoke()
        self.assertFalse(self.out.exists())
    def test_full_rectangle_zero_sample_and_literal_ids_kept(self):
        self.invoke();self.assertEqual(json.load(open(self.out/'validation.json'))['sample_ids'],['001','1','NA']);self.assertEqual((self.out/'contig_abundance.tsv').read_bytes(),self.contigs.read_bytes())
    def test_missing_sample_is_not_zero(self):
        self.crows=[r for r in self.crows if r['sample_id']!='1'];self.rejected('incomplete sample-feature')
    def test_missing_measurement_is_not_zero(self):self.crows.pop();self.rejected('incomplete sample-feature')
    def test_duplicate_measurement_rejected(self):self.crows.append(self.crows[0]);self.rejected('duplicate sample-feature')
    def test_missing_state_rejected(self):self.srows.pop();self.rejected('state sample set mismatch')
    def test_declared_empty_table_with_positive_features_rejected(self):self.prows=[];self.rejected('declared feature count')
    def test_false_state_total_rejected(self):self.srows[0]['eligible_read_alignments']=999;self.rejected('count total differs')
    def test_plasmid_measurement_cannot_differ_from_competitive_reference(self):
        self.prows[0]['coverage']='9.9';self.rejected('subset measurement differs')
    def test_equivalent_decimal_forms_are_equal(self):
        self.prows[0]['coverage']='0.2000000000000000000000';self.invoke()
    def test_negative_zero_is_the_same_measurement(self):
        self.prows[1]['coverage']='-0';self.invoke()
    def test_precision_beyond_decimal_context_cannot_mask_a_mismatch(self):
        self.crows[0]['coverage']='0.123456789012345678901234567890111'
        self.prows[0]['coverage']='0.123456789012345678901234567890222'
        self.rejected('subset measurement differs')
    def test_zero_features_require_explicit_empty_producer_state(self):
        self.crows=[];self.prows=[]
        for r in self.srows:r.update(reference_features=0,plasmid_features=0,eligible_read_alignments=0,plasmid_read_alignments=0,quantification_status='empty_catalogue')
        self.invoke();self.assertEqual(json.load(open(self.out/'validation.json'))['tables']['contigs']['features'],0)


if __name__=='__main__':unittest.main()
