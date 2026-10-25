import importlib.util
import json
import os
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('hotspot_runtime',ROOT/'bin/hotspot_runtime.py')
runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)


class HotspotRuntime(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def library(self,flags):
        package=self.root/'torch';(package/'lib').mkdir(parents=True)
        origin=package/'__init__.py';origin.write_text('')
        header=bytearray(64);header[:6]=b'\x7fELF\x02\x01';struct.pack_into('<Q',header,32,64);struct.pack_into('<HH',header,54,56,1)
        entry=bytearray(56);struct.pack_into('<II',entry,0,0x6474e551,flags)
        library=package/'lib/libtorch_cpu.so';library.write_bytes(header+entry+b'UNCHANGED_TEST_PAYLOAD')
        return origin,library

    def test_private_elf_change_never_mutates_original_or_cache_hardlink(self):
        origin,library=self.library(7);alias=self.root/'package-cache-link';os.link(library,alias)
        original=library.read_bytes();work=self.root/'private'
        with patch.object(runtime.importlib.util,'find_spec',return_value=SimpleNamespace(origin=str(origin))),patch.object(runtime.importlib.metadata,'version',return_value='EXPLICIT_UNIT_FIXTURE'):
            environment,metadata=runtime.runtime_environment(work)
        private=work/library.name;changed=[i for i,(a,b) in enumerate(zip(original,private.read_bytes())) if a!=b]
        self.assertEqual(changed,[68]);self.assertEqual(runtime.stack_flags(private),(68,6))
        self.assertEqual(library.read_bytes(),original);self.assertEqual(alias.read_bytes(),original)
        self.assertEqual(environment['LD_PRELOAD'].split()[0],str(private))
        self.assertEqual(metadata['private_elf_compatibility']['flags_before'],7)

    def test_no_executable_stack_flag_needs_no_private_rewrite(self):
        origin,library=self.library(6);original=library.read_bytes();work=self.root/'private'
        with patch.object(runtime.importlib.util,'find_spec',return_value=SimpleNamespace(origin=str(origin))),patch.object(runtime.importlib.metadata,'version',return_value='EXPLICIT_UNIT_FIXTURE'):
            _,metadata=runtime.runtime_environment(work)
        self.assertFalse(work.exists());self.assertIsNone(metadata['private_elf_compatibility']);self.assertEqual(library.read_bytes(),original)

    def test_malformed_elf_is_rejected_without_writing(self):
        for data in [b'',b'not an ELF',b'\x7fELF\x02\x01'+b'\0'*58]:
            file=self.root/'bad.so';file.write_bytes(data)
            with self.assertRaises((ValueError,struct.error)):runtime.stack_flags(file)
            self.assertEqual(file.read_bytes(),data)

    def test_resource_fingerprint_tracks_bytes_even_when_size_and_mtime_match(self):
        path=self.root/'parent.dict';path.write_bytes(b'valid fixture');stamp=path.stat();before=runtime.fingerprint(self.root)
        path.write_bytes(b'other fixture');os.utime(path,ns=(stamp.st_atime_ns,stamp.st_mtime_ns));after=runtime.fingerprint(self.root)
        self.assertEqual(before['parent.dict']['bytes'],after['parent.dict']['bytes'])
        self.assertNotEqual(before['parent.dict']['sha256'],after['parent.dict']['sha256'])


if __name__=='__main__':unittest.main()
