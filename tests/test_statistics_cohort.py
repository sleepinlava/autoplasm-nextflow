"""Every consumer must distinguish missing measurements from measured zeros."""
import csv,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


class StatisticsCohortTests(unittest.TestCase):
    def check_rejection(self, change, diagnostic):
        for script in ['diversity.R','differential_abundance.R','deseq2_plasmid.R','network_prepare.R']:
            with self.subTest(script=script),tempfile.TemporaryDirectory() as directory:
                d=Path(directory);column='plasmid_id' if script=='deseq2_plasmid.R' else 'contig_id';rows=[['001','F1','2','2'],['1','F1','0','0'],['001','F2','3','3'],['1','F2','4','4']];meta=[['001','A'],['1','B']]
                if change=='missing_sample':rows=[r for r in rows if r[0]!='1']
                elif change=='missing_cell':rows.pop()
                elif change=='duplicate_cell':rows.append(rows[0])
                elif change=='unexpected_sample':rows[0][0]='UNKNOWN'
                elif change=='duplicate_metadata':meta.append(meta[0])
                elif change=='blank_metadata':meta[0][0]=''
                ab=d/'ab.tsv';ab.write_text('sample_id\t'+column+'\tcoverage\traw_count\n'+'\n'.join('\t'.join(r) for r in rows)+'\n');metadata=d/'meta.tsv';metadata.write_text('sample_id\tgroup\n'+'\n'.join('\t'.join(r) for r in meta)+'\n');out=d/'out.tsv';cmd=['Rscript',str(ROOT/'bin'/script),'--abundance',str(ab),'--metadata',str(metadata)]
                cmd+=['--out-metrics',str(out),'--out-beta',str(d/'beta.tsv')] if script=='diversity.R' else ['--output' if script=='deseq2_plasmid.R' else '--out',str(out)]
                r=subprocess.run(cmd,capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertIn(diagnostic,r.stderr);self.assertFalse(out.exists())
    def test_missing_sample_is_not_zero(self):self.check_rejection('missing_sample','sample set mismatch')
    def test_missing_cell_is_not_zero(self):self.check_rejection('missing_cell','incomplete sample-feature')
    def test_duplicate_measurement_rejected(self):self.check_rejection('duplicate_cell','duplicate sample-feature')
    def test_unexpected_sample_rejected(self):self.check_rejection('unexpected_sample','sample set mismatch')
    def test_duplicate_metadata_rejected(self):self.check_rejection('duplicate_metadata','duplicate metadata')
    def test_blank_metadata_id_rejected(self):self.check_rejection('blank_metadata','nonempty sample IDs')


if __name__=='__main__':unittest.main()
