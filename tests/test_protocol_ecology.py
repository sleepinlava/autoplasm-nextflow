"""Actual vegan inference, formula qualification and ANCOM-BC2 eligibility contracts."""
import csv,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


class ProtocolEcology(unittest.TestCase):
    def test_system_function_enrichment_and_gene_order_pdf_use_actual_R(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            for name in ['annotations','systems','catalogue']:(d/name).mkdir()
            (d/'annotations/functions.tsv').write_text('plasmid_id\tgene_id\tsource\tterm\np0\tg0\tKEGG_ko\tK1\np1\tg1\tKEGG_ko\tK1\n')
            (d/'annotations/genes.tsv').write_text('gene_id\tplasmid_id\tstart\tend\tstrand\n'+'g0\tp0\t20\t90\t+\ng1\tp1\t40\t100\t-\n')
            (d/'annotations/gene_family_clusters.tsv').write_text('gene_id\tfamily_id\ng0\tF1\ng1\tF1\n')
            (d/'systems/membership.tsv').write_text('plasmid_id\tsystem_id\tmembership_grade\np0\tSYS\tsystem_member\np1\tSYS\tsystem_member\n')
            (d/'catalogue/structure.tsv').write_text('plasmid_id\np0\np1\np2\np3\n')
            (d/'catalogue/features.tsv').write_text('feature_id\tlength_bp\np0\t200\np1\t200\np2\t200\np3\t200\n')
            command=['Rscript',str(ROOT/'bin/protocol_function_enrichment.R'),str(d/'annotations'),str(d/'systems'),str(d/'catalogue'),str(d/'enrichment.tsv'),str(d/'figures')]
            r=subprocess.run(command,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
            self.assertTrue((d/'figures/SYS.gene_order.pdf').read_bytes().startswith(b'%PDF'))
            self.assertEqual(json.loads((d/'figures/status.json').read_text())['status'],'measured')
            with (d/'enrichment.tsv').open() as f:terms=list(csv.DictReader(f,delimiter='\t'))
            self.assertEqual(len(terms),1);self.assertTrue(0<float(terms[0]['q_value'])<=1)

    def invoke(self,groups,extra=None,formula='group',block=''):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);d=Path(tmp.name)
        matrix=[[1,9,1],[2,8,1],[1,8,2],[8,1,1],[9,2,1],[8,1,2]]
        ab=d/'ab';ab.write_text('plasmid_id\tsample_id\tcoverage\n'+''.join(f'P{j}\tS{i}\t{x}\n' for i,row in enumerate(matrix) for j,x in enumerate(row)))
        md=d/'md';md.write_text('sample_id\tgroup\tsubject\n'+''.join(f'S{i}\t{groups[i]}\tU{i%3}\n' for i in range(6)))
        cmd=['Rscript',str(ROOT/'bin/diversity.R'),'--abundance',str(ab),'--metadata',str(md),'--out-metrics',str(d/'alpha'),'--out-beta',str(d/'beta'),'--inference-dir',str(d/'inference'),'--beta-normalization','tss','--formula',formula,'--block',block,'--permutations','19']
        r=subprocess.run(cmd,capture_output=True,text=True)
        return r,d

    def test_actual_vegan_permanova_dispersion_and_ordination(self):
        r,d=self.invoke(['A']*3+['B']*3,block='subject');self.assertEqual(r.returncode,0,r.stderr)
        status=json.loads((d/'inference/status.json').read_text());self.assertEqual(status['status'],'measured');self.assertEqual(status['dispersion'],'measured')
        with (d/'inference/permanova.tsv').open() as f:terms=list(csv.DictReader(f,delimiter='\t'))
        self.assertIn('group',{x['term'] for x in terms});self.assertEqual(len((d/'inference/ordination.tsv').read_text().splitlines()),7)
        self.assertTrue((d/'inference/ordination.pdf').read_bytes().startswith(b'%PDF'))

    def test_single_group_produces_ordination_with_explicit_inference_skip(self):
        r,d=self.invoke(['A']*6);self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(json.loads((d/'inference/status.json').read_text())['status'],'ordination_only')

    def test_missing_covariate_is_an_error(self):
        r,d=self.invoke(['A']*3+['B']*3,formula='group + nonexistent');self.assertNotEqual(r.returncode,0);self.assertIn('Design fields missing',r.stderr)

    def test_ancombc_empty_cohort_does_not_invent_negative_tests(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);(d/'ab').write_text('plasmid_id\tsample_id\traw_count\n');(d/'md').write_text('sample_id\tgroup\nA\tX\nB\tX\nC\tY\nD\tY\n')
            cmd=['Rscript',str(ROOT/'bin/ancombc2_plasmid.R'),'--abundance',str(d/'ab'),'--metadata',str(d/'md'),'--output',str(d/'out'),'--formula','group','--random','','--prevalence','.1','--replicates','2','--threads','1']
            r=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(json.loads((d/'out/status.json').read_text())['status'],'ineligible')
            self.assertEqual((d/'out/coefficients.tsv').read_text(),'taxon\n')

    def test_ancombc_positive_counts_without_comparable_groups_are_ineligible(self):
        for metadata,reason in [('sample_id\tgroup\nA\tX\nB\tX\nC\tX\n','insufficient_group_replicates'),
                                ('sample_id\nA\nB\nC\n','no_group_column')]:
            with self.subTest(reason=reason),tempfile.TemporaryDirectory() as tmp:
                d=Path(tmp);(d/'ab').write_text('plasmid_id\tsample_id\traw_count\nP\tA\t10\nP\tB\t20\nP\tC\t30\n');(d/'md').write_text(metadata)
                command=['Rscript',str(ROOT/'bin/ancombc2_plasmid.R'),'--abundance',str(d/'ab'),'--metadata',str(d/'md'),'--output',str(d/'out'),'--formula','group','--random','','--prevalence','.1','--replicates','3','--threads','1']
                r=subprocess.run(command,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
                state=json.loads((d/'out/status.json').read_text());self.assertEqual(state['status'],'ineligible');self.assertEqual(state['reason'],reason)
                self.assertEqual((d/'out/coefficients.tsv').read_text(),'taxon\n')

if __name__=='__main__':unittest.main()
