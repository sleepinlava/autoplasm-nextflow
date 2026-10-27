"""Native runtime read-set controls; these methods perform no IS inference."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('isescan_resource_test',ROOT/'bin/isescan_runtime_resources.py')
resolver=importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolver)


class RuntimeResources(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.sequence=self.root/'sequence [1].fna'
        self.sequence.write_text('>EXPLICIT_READSET_CONTROL\nACGT\n')
        self.runtime={'scope':'EXPLICIT_READSET_CONTROL_NO_INFERENCE'}
        self.entry=resolver.executable('isescan.py')

    def tearDown(self):
        self.temp.cleanup()

    def capture(self):
        return resolver.capture(self.runtime,str(self.sequence),'sample.isescan_out')

    def test_fixed_source_profiles_and_all_training_members(self):
        value=self.capture()
        self.assertEqual(value['version'],'1.7.3')
        self.assertEqual(len(value['resources']['source']),8)
        model=value['resources']['fraggenescan_training']
        self.assertEqual(len(model),18)  # root directory plus17regular resources
        self.assertTrue({'./illumina_5','./complete','./gene','./rgene','./pwm'}<=set(p['path'] for p in model))
        self.assertEqual(value['resources']['sequence'][0]['sha256'],hashlib.sha256(self.sequence.read_bytes()).hexdigest())

    def test_loaded_ssw_path_and_bytes_are_explicit(self):
        value=self.capture()
        path=Path(value['resolved_locations']['ssw_loaded_object'])
        self.assertEqual(path.name,'libssw.so')
        self.assertEqual(value['resources']['ssw_loaded_object'][0]['sha256'],hashlib.sha256(path.read_bytes()).hexdigest())

    def test_source_version_mismatch_refused_before_import_or_execution(self):
        binary=self.root/'isescan.py'
        binary.write_text("#!/usr/bin/env python3\nversion='1.7.2'\n")
        binary.chmod(0o755)
        with patch.dict(os.environ,PATH=str(self.root)+':'+os.environ['PATH']):
            with self.assertRaisesRegex(ValueError,'requires native1.7.3'):
                self.capture()

    def test_profile_location_follows_argv0_not_source_file_realpath(self):
        (self.root/'isescan.py').symlink_to(self.entry)
        with patch.dict(os.environ,PATH=str(self.root)+':'+os.environ['PATH']):
            with self.assertRaises(FileNotFoundError) as error:
                self.capture()
        self.assertIn(str(self.root/'pHMMs'),str(error.exception))

    def test_fraggenescan_models_follow_invoked_wrapper_directory(self):
        wrapper=resolver.executable('run_FragGeneScan.pl')
        (self.root/'run_FragGeneScan.pl').symlink_to(wrapper)
        (self.root/'FragGeneScan').symlink_to(wrapper.parent/'FragGeneScan')
        with patch.dict(os.environ,PATH=str(self.root)+':'+os.environ['PATH']):
            with self.assertRaises(FileNotFoundError) as error:
                self.capture()
        self.assertIn(str(self.root/'train'),str(error.exception))

    def test_tampered_receipt_prevents_actual_exec(self):
        output=self.root/'should-not-exist'
        value=resolver.capture(self.runtime,str(self.sequence),str(output))
        value['version']='UNTRUSTED_EDIT'
        receipt=self.root/'identity.json'
        receipt.write_text(json.dumps(value))
        cmd=[sys.executable,str(ROOT/'bin/isescan_runtime_resources.py'),'--runtime-base64',base64.b64encode(json.dumps(self.runtime).encode()).decode(),
             '--seqfile',str(self.sequence),'--result-prefix',str(output),'--threads','1','--verify',str(receipt),'--execute']
        result=subprocess.run(cmd,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('differ from pre-lookup identity',result.stderr)
        self.assertFalse(output.exists())


if __name__=='__main__':
    unittest.main()
