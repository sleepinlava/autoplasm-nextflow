"""Actual2.0.5 parser/read-set and approved topology; no search inference."""
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'bin'))
import integronfinder_runtime_resources as resolver


@unittest.skipUnless(importlib.util.find_spec('integron_finder'), 'Native IntegronFinder2.0.5 test environment required')
class Resources(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.fasta=self.root/'input.fst';self.fasta.write_text('>ACBA.007.P01_13\n'+'ACGT'*30+'\n')
        import integron_finder
        self.package=Path(integron_finder.__file__).parent

    def tearDown(self): self.tmp.cleanup()

    def capture(self,*args): return resolver.capture({'scope':'EXPLICIT_READ_SET_CONTROL'},[str(self.fasta),*args])

    def test_wrong_console_interpreter_refused(self):
        entry=self.root/'integron_finder';entry.write_text('#!/definitely/not/the/probe/python\n')
        with self.assertRaisesRegex(ValueError,'interpreter differs'):
            resolver.verify_entrypoint_interpreter(entry)

    def test_default_three_models_and_unknown_linear(self):
        value=self.capture();self.assertEqual(len(value['resources']['models']),3)
        self.assertEqual(value['topology']['replicons'][0]['topology'],'lin')
        self.assertEqual(value['topology']['replicons'][0]['source'],'unknown_treated_as_linear')
        self.assertNotIn('cpu',value['parsed_arguments'])

    def test_explicit_cli_and_file_precedence(self):
        self.assertEqual(self.capture('--circ')['topology']['replicons'][0]['topology'],'circ')
        topology=self.root/'topology.tsv';topology.write_text('ACBA.007.P01_13 lin\n')
        value=self.capture('--circ','--topology-file',str(topology));self.assertEqual(value['topology']['replicons'][0]['topology'],'lin')
        self.assertEqual(value['resources']['topology_file'],resolver.resource(topology))

    def test_mixed_headers_keep_explicit_circular(self):
        self.fasta.write_text('>C topology=circular\n'+'ACGT'*30+'\n>U\n'+'TGCA'*30+'\n')
        self.assertEqual([(r['id'],r['topology']) for r in self.capture()['topology']['replicons']],[('C','circ'),('U','lin')])

    def test_conflict_and_duplicate_ids_refuse(self):
        self.fasta.write_text('>C circular=true topology=linear\nACGT\n')
        with self.assertRaisesRegex(ValueError,'Conflicting'): self.capture()
        self.fasta.write_text('>C\nACGT\n>C\nACGT\n')
        with self.assertRaisesRegex(ValueError,'Duplicate'): self.capture()

    def test_selected_external_cm_same_stat_mutation(self):
        model=self.root/'selected.cm';shutil.copy2(self.package/'data/Models/attc_4.cm',model)
        first=self.capture('--attc-model',str(model));st=model.stat();data=bytearray(model.read_bytes());data[data.index(b'DATE')+9]=ord('X');model.write_bytes(data);os.utime(model,ns=(st.st_atime_ns,st.st_mtime_ns));second=self.capture('--attc-model',str(model))
        self.assertNotEqual(first['resources']['models'],second['resources']['models'])
        self.assertEqual(first['resolved_locations']['models']['model_attc_path'],str(model))

    def test_functional_bank_list_tracks_external_glob_members(self):
        models=self.root/'outside';models.mkdir();shutil.copy2(self.package/'data/Models/integron_integrase.hmm',models/'one.hmm')
        listing=self.root/'banks.txt';listing.write_text(str(models/'*.hmm')+'\n')
        first=self.capture('--path-func-annot',str(listing));self.assertEqual(len(first['resources']['functional_profiles']),1)
        shutil.copy2(models/'one.hmm',models/'two.hmm');second=self.capture('--path-func-annot',str(listing));self.assertEqual(len(second['resources']['functional_profiles']),2)
        skipped=self.capture('--path-func-annot',str(listing),'--no-proteins');self.assertNotIn('functional_profiles',skipped['resources'])

    def test_functional_default_and_native_no_proteins_branch(self):
        selected=self.capture('--func-annot');self.assertIn('functional_bank_source',selected['resources'])
        skipped=self.capture('--func-annot','--no-proteins');self.assertNotIn('functional_bank_source',skipped['resources'])

    def test_gembase_explicit_path_tracks_lst_and_proteins(self):
        bank=self.root/'gembase';(bank/'LST').mkdir(parents=True);(bank/'Proteins').mkdir()
        (bank/'LST/input.lst').write_text('EXPLICIT_READ_SET_ONLY_NOT_A_GEMBASE_LIST\n');(bank/'Proteins/input.prt').write_text('>OBSERVER\nAAA\n')
        value=self.capture('--gembase-path',str(bank));self.assertIn('gembase_list',value['resources']);self.assertIn('gembase_proteins',value['resources'])

    def test_external_annotation_parser_and_proteins_hashed(self):
        proteins=self.root/'proteins.faa';proteins.write_text('>READ_SET_ONLY\nAAA\n');parser=self.root/'custom.py';parser.write_text('# EXPLICIT_READ_SET_ONLY_NOT_EXECUTED\n')
        value=self.capture('--prot-file',str(proteins),'--annot-parser',str(parser));self.assertEqual(value['resources']['annot_parser'],resolver.resource(parser));self.assertEqual(value['resources']['prot_file'],resolver.resource(proteins))

    def test_symlink_cycles_and_dangling_fail(self):
        data=self.root/'data';data.mkdir();link=data/'link';link.symlink_to(data,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'cycle'): resolver.resource(data)
        link.unlink();link.symlink_to(data/'missing')
        with self.assertRaises(FileNotFoundError): resolver.resource(data)


if __name__=='__main__': unittest.main()
