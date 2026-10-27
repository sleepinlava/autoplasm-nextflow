"""Verify the pinned full source and reject private gitlink content corruption."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('anvio_checked', ROOT / 'bin/anvio_checked.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AnvioSubmoduleTests(unittest.TestCase):
    def test_archive_lock_and_runtime_source_lock_agree(self):
        lock = json.loads((ROOT / 'tests/anvio-submodules.lock.json').read_text())
        expected = {row['path']: {key: row[key] for key in ['commit', 'files', 'digest']}
                    for row in lock['submodules']}
        self.assertEqual(len(expected), 13)
        self.assertEqual(expected, module.SOURCE_SUBMODULES)

    def test_complete_real_source_and_private_same_stat_corruption(self):
        source = os.environ.get('AUTOPLASM_ANVIO_COMPLETE_SOURCE')
        if not source:
            self.skipTest('Pinned complete source must be supplied explicitly')
        source = Path(source).resolve()
        self.assertEqual(module.verify_source(source), module.SOURCE_DIGEST)
        with tempfile.TemporaryDirectory(prefix='anvio-source-control-') as temporary:
            private = Path(temporary) / 'source'
            shutil.copytree(source, private, symlinks=True)
            target = private / 'anvio/data/interactive/lib/bootstrap/dist/js/bootstrap.min.js'
            original = target.read_bytes()
            before = target.stat()
            target.write_bytes(bytes([original[0] ^ 1]) + original[1:])
            os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
            with self.assertRaisesRegex(ValueError, 'Missing or changed pinned.*submodule'):
                module.verify_source(private)
            target.write_bytes(original)
            os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
            self.assertEqual(module.verify_source(private), module.SOURCE_DIGEST)
            target.unlink()
            with self.assertRaisesRegex(ValueError, 'Missing or changed pinned.*submodule'):
                module.verify_source(private)


if __name__ == '__main__':
    unittest.main()
