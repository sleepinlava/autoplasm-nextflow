"""Native fixed2.1.6 parser/read-set controls; no classifier accuracy claim."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bin'))
import plasmidfinder_runtime_resources as helper

ROOT=Path(__file__).resolve().parents[1]
PREFIX=ROOT/'results/tool-audit/runtime/plasmidfinder-2.1.6-py310'


class NativeReadset(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.db=self.base/'database'
        shutil.copytree(PREFIX/'share/plasmidfinder-2.1.6/database',self.db)
        self.entry=PREFIX/'bin/plasmidfinder.py'
        self.sequence=self.base/'input.fsa';self.sequence.write_text('>control\nACGTACGT\n')
        self.argv=['-i',str(self.sequence),'-o',str(self.base),'-p',str(self.db),'-x']

    def capture(self,extra=()):
        return helper.capture({},self.argv+list(extra))

    def test_native_defaults_and_full_directory(self):
        result=self.capture()
        self.assertEqual(len(result['selected_databases']),9)
        self.assertEqual(result['parsed_arguments']['min_cov'],.60)
        self.assertEqual(result['parsed_arguments']['threshold'],.90)
        self.assertEqual(result['file_format'],'fasta')
        self.assertEqual(len(result['resources']['database']),len(helper.resource(self.db)))
        self.assertTrue(result['resources']['cgecore_code'])

    def test_explicit_database_and_taxonomy_use_native_selection(self):
        self.assertEqual(self.capture(['-d','enterobacteriaceae'])['selected_databases'],['enterobacteriaceae'])
        selected=self.capture(['--speciesinfo_json',json.dumps(['bacteria','enterobacteriaceae'])])
        self.assertEqual(selected['selected_databases'],['enterobacteriaceae'])
        self.assertEqual(len(self.capture(['--speciesinfo_json','["unmatched"]'])['selected_databases']),9)

    def test_invalid_native_database_and_legacy_refused(self):
        with self.assertRaises(SystemExit):self.capture(['-d','absent'])
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):self.capture(['--legacy'])

    def test_quiet_restores_stdout(self):
        stdout=sys.stdout
        self.assertTrue(self.capture(['-q'])['parsed_arguments']['quiet'])
        self.assertIs(sys.stdout,stdout)

    def test_full_directory_sidecar_and_symlink_target_changes(self):
        external=self.base/'external';external.write_bytes(b'AA')
        (self.db/'external-sidecar').symlink_to(external)
        before=self.capture();st=external.stat();external.write_bytes(b'BB');os.utime(external,ns=(st.st_atime_ns,st.st_mtime_ns))
        self.assertNotEqual(before['resources']['database'],self.capture()['resources']['database'])
        (self.db/'cycle').symlink_to(self.db,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'cycle'):self.capture()

    def test_explicit_method_binary_is_identified(self):
        binary=self.base/'blastn';shutil.copy2(PREFIX/'bin/blastn',binary)
        result=self.capture(['-mp',str(binary)])
        self.assertEqual(result['resolved_locations']['method'],str(binary))
        self.assertEqual(result['resources']['method'],helper.resource(binary))

    def test_exact_source_and_interpreter_guard(self):
        bad=self.base/'plasmidfinder.py';bad.write_text(self.entry.read_text()+'\n# changed source\n')
        with self.assertRaisesRegex(ValueError,'exact native2.1.6'):helper.native_configuration(bad,self.argv)
        bad.write_text('#!/bin/false\n')
        with self.assertRaisesRegex(ValueError,'interpreter differs'):helper.verify_entrypoint_interpreter(bad)

    def test_native_fastq_branch_and_inputs(self):
        self.sequence.write_text('@control\nACGTACGT\n+\nIIIIIIII\n')
        result=self.capture()
        self.assertEqual(result['file_format'],'fastq')
        self.assertTrue(result['resolved_locations']['method'].endswith('/kma'))
        self.assertEqual(result['resources']['inputs'],[helper.resource(self.sequence)])


if __name__=='__main__':unittest.main()
