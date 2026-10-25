"""Candidate/output contracts only; the compatible CLI here is an explicit observer."""
import argparse
import gzip
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('copla_candidates',ROOT/'bin/run_copla_candidates.py')
adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)

OBSERVER='''import sys,shutil
from pathlib import Path
sequence,graph,reflist,output,*flags=sys.argv[1:]
assert flags[0]=='-t' and flags[1] in ['linear','circular']
assert Path(graph).is_file() and Path(reflist).is_file()
text=Path(sequence).read_text();lines=text.splitlines()
assert sum(line.startswith('>') for line in lines)==1
dna=''.join(line for line in lines if not line.startswith('>'))
assert dna in ['ACGTACGT','TTTTCCCCAAAAGGGG']
if dna=='TTTTCCCCAAAAGGGG' and Path('bin/fail_second').exists():raise SystemExit(7)
out=Path(output);out.mkdir(parents=True);prefix=out/Path(sequence).name
shutil.copyfile(sequence,prefix)
Path(str(prefix)+'.faa').write_text('')
Path(str(prefix)+'.ani.tsv').write_text('THIS IS A BAIT TABLE, NOT A PTU PREDICTION\\n')
Path(str(prefix)+'.related_plasmids.tsv').write_text('#AccessionVersion\\tPTU_Ref\\tNote\\n')
Path(str(prefix)+'.qry_info.tsv').write_text('#Total bp\\tMOB\\tMPF\\tReplicon\\tAMR\\n'+str(len(dna))+'\\t-\\t-\\t-\\t-\\n')
if not Path('bin/missing_prediction').exists():
 label='PTU-A' if dna=='ACGTACGT' else 'PTU-B'
 Path(str(prefix)+'.ptu_prediction.tsv').write_text('#Predicted_PTU\\tHost_Range\\tScore\\tNotes\\n'+label+'\\tI\\t0.9500\\tExplicit DNA-driven observer\\n')
'''


class CandidateContracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);previous=Path.cwd();os.chdir(self.root)
        self.addCleanup(os.chdir,previous)
        self.input=self.root/'candidate input.fna'
        self.input.write_text('>A\nACGTACGT\n>B\nTTTTCCCCAAAAGGGG\n')
        self.install=self.root/"installation's directory";(self.install/'bin').mkdir(parents=True)
        (self.install/'bin/copla.py').write_text(OBSERVER)
        (self.install/'bin/ani.rb').write_text('# unused, observer only\n')
        for name in ['Copla_RS84','MOBscan_171004','MacSyFinder_190530/Conjugation','PlasmidFinder_190731','CARD_201015']:
            (self.install/'databases'/name).mkdir(parents=True)
        self.reference=self.install/'databases/Copla_RS84/REF.1.fna';self.reference.write_text('>REF.1\nACGT\n')
        self.list=self.root/'references.fofn';self.list.write_text(str(self.reference)+'\n')
        self.graph=self.root/'graph.pickle';self.graph.write_text('OBSERVER_FIXTURE_NOT_A_REAL_GRAPH\n')
        self.macsy=self.root/'macsy';(self.macsy/'bin').mkdir(parents=True)
        (self.macsy/'bin/macsyfinder').write_text('# unused observer marker\n')
        self.args=argparse.Namespace(assembly=str(self.input),installation=str(self.install),refgraph=str(self.graph),
             reflist=str(self.list),macsyfinder=str(self.macsy),threads=1,output='sample.copla.tsv',raw='sample.copla')

    def launch_observer(self):
        # Only source/format behavior is tested. No graph, ANI or model executes.
        with patch.object(adapter.shutil,'which',return_value='/explicit-unused-observer-binary'):
            return adapter.run(self.args)

    def test_independent_DNA_records_never_merge_or_select_bait_table(self):
        self.assertEqual(self.launch_observer(),0)
        import csv
        with Path(self.args.output).open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
        self.assertEqual([(r['contig_id'],r['length'],r['predicted_ptu']) for r in rows],[('A','8','PTU-A'),('B','16','PTU-B')])
        manifest=json.loads((Path(self.args.raw)/'entities.json').read_text())
        self.assertEqual([r['length'] for r in manifest['entities']],[8,16])
        self.assertFalse(manifest['source_patch']['applied'])
        self.assertFalse((Path(self.args.raw)/'databases').exists())
        self.assertEqual(self.input.read_text(),'>A\nACGTACGT\n>B\nTTTTCCCCAAAAGGGG\n')

    def test_second_candidate_failure_does_not_publish_partial_aggregate(self):
        (self.install/'bin/fail_second').touch()
        with self.assertRaisesRegex(ValueError,'failed for candidate B'):self.launch_observer()
        self.assertFalse(Path(self.args.output).exists());self.assertFalse(Path(self.args.raw).exists())
        self.assertTrue(Path('copla_program/results/candidate_000001/candidate_000001.fna.ptu_prediction.tsv').exists())

    def test_missing_prediction_cannot_fall_back_to_another_table(self):
        (self.install/'bin/missing_prediction').touch()
        with self.assertRaisesRegex(ValueError,'Missing exact COPLA product'):self.launch_observer()
        self.assertFalse(Path(self.args.output).exists())

    def test_duplicate_ID_is_rejected_before_program_execution(self):
        self.input.write_text('>same\nACGT\n>same\nTTTT\n')
        with self.assertRaisesRegex(ValueError,'unique candidate IDs'):self.launch_observer()
        self.assertFalse(Path('copla_program').exists())

    def test_empty_ID_sequence_and_invalid_alphabet_are_rejected(self):
        for text in ['> \nACGT\n','>A\n','>A\nACGZ\n','ACGT\n>A\nACGT\n']:
            self.input.write_text(text)
            with self.subTest(text=text):
                with self.assertRaises(ValueError):adapter.candidates(self.input)

    def test_gzip_uppercase_and_wrapping_preserve_complete_DNA(self):
        p=self.input.with_suffix('.fna.GZ');p.write_bytes(gzip.compress(b'>A\nACGT\nACGT\n>B\nTTTTCCCC\nAAAAGGGG\n'))
        self.assertEqual(adapter.candidates(p),adapter.candidates(self.input))

    def test_corrupt_gzip_is_not_an_empty_candidate_set(self):
        p=self.input.with_suffix('.fna.gz');p.write_bytes(b'broken gzip')
        with self.assertRaises(OSError):adapter.candidates(p)

    def test_only_explicit_topology_annotations_enable_circular_mode(self):
        self.input.write_text('>A circular contig\nACGT\n>B topology=circular\nTTTT\n>C circular=false\nCCCC\n')
        result=adapter.candidates(self.input)
        self.assertEqual([r['topology'] for r in result],['linear','circular','linear'])
        self.assertEqual(result[0]['topology_source'],'unknown_treated_as_linear')

    def test_conflicting_explicit_topologies_are_rejected(self):
        self.input.write_text('>A topology=circular circular=false\nACGT\n')
        with self.assertRaisesRegex(ValueError,'Conflicting'):adapter.candidates(self.input)

    def test_external_reference_file_is_not_a_hidden_dependency(self):
        external=self.root/'OTHER.fna';external.write_text('>OTHER\nACGT\n')
        self.list.write_text(str(external)+'\n')
        with self.assertRaisesRegex(ValueError,'outside the declared installation'):adapter.reference_files(self.install,self.list)

    def test_reference_directory_name_is_not_a_release_constraint(self):
        folder=self.install/"custom reference directory's";folder.mkdir()
        reference=folder/'REF.1.fna';reference.write_text('>REF.1\nACGT\n')
        self.list.write_text(str(reference)+'\n')
        self.assertEqual(adapter.reference_files(self.install,self.list),[reference])
        self.assertEqual(self.launch_observer(),0)
        self.assertFalse((Path(self.args.raw)/'reference_sequences').exists())

    def test_missing_empty_duplicate_and_compressed_reference_entries_fail(self):
        values=['',str(self.reference)+'\n\n',str(self.reference)+'\n'+str(self.reference)+'\n',str(self.reference)+'.gz\n']
        for value in values:
            self.list.write_text(value)
            with self.subTest(value=value):
                with self.assertRaises(ValueError):adapter.reference_files(self.install,self.list)

    def test_prediction_schema_rows_and_finite_score_are_required(self):
        p=self.root/'prediction.tsv'
        for text in ['wrong\n','\t'.join(adapter.PREDICTION)+'\n',
                     '\t'.join(adapter.PREDICTION)+'\nPTU-X\tI\tnan\tNote\n',
                     '\t'.join(adapter.PREDICTION)+'\nPTU-X\tI\t1.01\tNote\n',
                     '\t'.join(adapter.PREDICTION)+'\nPTU-X\tVII\t0.5\tNote\n']:
            p.write_text(text)
            with self.subTest(text=text):
                with self.assertRaises(ValueError):adapter.prediction(p)

    def test_unclassified_result_is_valid_not_a_missing_product(self):
        p=self.root/'prediction.tsv';p.write_text('\t'.join(adapter.PREDICTION)+'\n-\t-\t1.0000\tComponent has size1\n')
        self.assertEqual(adapter.prediction(p)['#Predicted_PTU'],'-')

    def test_stale_output_is_rejected(self):
        Path(self.args.output).touch()
        with self.assertRaisesRegex(ValueError,'pre-existing'):self.launch_observer()

    def test_nonpositive_threads_are_rejected(self):
        self.args.threads=0
        with self.assertRaisesRegex(ValueError,'threads must be positive'):self.launch_observer()


if __name__=='__main__':unittest.main()
