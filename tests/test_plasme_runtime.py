import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('runtime',ROOT/'bin/plasme_runtime.py')
runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)


def elf(path,flags=7,stacks=1):
    header=bytearray(64)
    header[:6]=b'\x7fELF\x02\x01'
    struct.pack_into('<Q',header,32,64)
    struct.pack_into('<HH',header,54,56,stacks)
    body=b''.join(struct.pack('<II',0x6474e551,flags)+b'\0'*48 for _ in range(stacks))
    path.write_bytes(bytes(header)+body+b'unchanged executable code payload')


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.source=self.root/'source';self.source.mkdir()
        for name in ['PLASMe.py','bio_script.py','trans_data.py','trans_model.py']:(self.source/name).write_text('# fixture only\n')
        self.db=self.root/'db';self.db.mkdir()
        self.resources=['plsdb_Mar30.dmnd','plsdb_taxon.tsv','plas_overlap.csv','plas_chrom_thres.csv','plsdb_Mar30.clusters.p2a',
                        'plsdb_Mar30.nin','plsdb_Mar30.nhr','plsdb_Mar30.nsq']
        for name in self.resources:(self.db/name).write_text('VALIDATION_FIXTURE_NOT_REAL_DATABASE\n')
        (self.db/'trans_model').mkdir()
        self.assembly=self.root/'input.fasta';self.assembly.write_text('>fixture\nACGT\n')
        self.args=argparse.Namespace(source_dir=str(self.source),database=str(self.db),assembly=str(self.assembly),
                output=str(self.root/'output.fasta'),threads=1,runtime_record=str(self.root/'runtime.json'))

    def test_only_stack_permission_changes_and_cache_hardlink_is_preserved(self):
        cache=self.root/'cache.so';elf(cache)
        installed=self.root/'installed.so';os.link(cache,installed)
        before=cache.read_bytes();record=runtime.clear_stack(installed)
        expected=bytearray(before);struct.pack_into('<I',expected,68,6)
        self.assertEqual(installed.read_bytes(),bytes(expected))
        self.assertEqual(cache.read_bytes(),before)
        self.assertNotEqual(cache.stat().st_ino,installed.stat().st_ino)
        self.assertEqual((record['flags_before'],record['flags_after']),(7,6))

    def test_already_nonexecutable_stack_is_unchanged(self):
        path=self.root/'library.so';elf(path,flags=6)
        before=path.read_bytes();inode=path.stat().st_ino
        record=runtime.clear_stack(path)
        self.assertEqual(path.read_bytes(),before);self.assertEqual(path.stat().st_ino,inode)
        self.assertEqual(record['before_sha256'],record['after_sha256'])

    def test_invalid_elf_is_rejected_without_writing(self):
        path=self.root/'library.so';path.write_bytes(b'not an ELF library')
        with self.assertRaises(ValueError):runtime.clear_stack(path)
        self.assertEqual(path.read_bytes(),b'not an ELF library')

    def test_missing_or_ambiguous_stack_headers_are_rejected(self):
        path=self.root/'library.so'
        for count in [0,2]:
            with self.subTest(count=count):
                elf(path,stacks=count);before=path.read_bytes()
                with self.assertRaisesRegex(ValueError,'one GNU_STACK'):runtime.clear_stack(path)
                self.assertEqual(path.read_bytes(),before)

    def test_missing_source_members_stop_before_runtime(self):
        for path in self.source.iterdir():
            data=path.read_bytes();path.unlink()
            with self.subTest(name=path.name):
                with self.assertRaisesRegex(ValueError,'Missing PLASMe source'):runtime.run(self.args)
            path.write_bytes(data)

    def test_missing_assembly_stops_before_runtime(self):
        self.assembly.unlink()
        with self.assertRaisesRegex(ValueError,'input assembly'):runtime.run(self.args)

    def test_missing_resources_stop_before_runtime(self):
        for name in self.resources:
            path=self.db/name;data=path.read_bytes();path.unlink()
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError,'Missing prepared PLASMe'):runtime.run(self.args)
            path.write_bytes(data)

    def test_empty_resources_are_not_accepted(self):
        path=self.db/'plsdb_Mar30.dmnd';path.write_bytes(b'')
        with self.assertRaisesRegex(ValueError,'Missing prepared PLASMe'):runtime.run(self.args)

    def test_missing_model_directory_stops_before_runtime(self):
        (self.db/'trans_model').rmdir()
        with self.assertRaisesRegex(ValueError,'model directory'):runtime.run(self.args)

    def test_nonpositive_threads_are_rejected(self):
        for value in [0,-1]:
            self.args.threads=value
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError,'threads must be positive'):runtime.run(self.args)

    def test_existing_outputs_refuse_stale_reuse(self):
        for suffix in ['', '_report.csv']:
            path=Path(self.args.output+suffix);path.touch()
            with self.subTest(suffix=suffix):
                with self.assertRaisesRegex(ValueError,'refusing stale result'):runtime.run(self.args)
            path.unlink()

    def test_absent_executable_is_not_an_empty_prediction(self):
        with patch.object(runtime.shutil,'which',return_value=None):
            with self.assertRaisesRegex(ValueError,'Missing PLASMe executable'):runtime.run(self.args)

    def test_absent_torch_is_not_an_empty_prediction(self):
        with patch.object(runtime.importlib.util,'find_spec',return_value=None):
            with self.assertRaisesRegex(ValueError,'pinned PyTorch'):runtime.runtime_environment(self.root/'private')
        self.assertFalse((self.root/'private').exists())


if __name__=='__main__':unittest.main()
