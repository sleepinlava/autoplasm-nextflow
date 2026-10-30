"""Filesystem identity controls; no biological input or scientific execution."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bin'))
from mobsuite_runtime_resources import resource, blast_database


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_same_size_mtime_mutation_and_restoration(self):
        path = self.root / 'metadata'
        path.write_text('original')
        before = resource(self.root)
        timestamp = path.stat()
        path.write_text('modified')
        os.utime(path, ns=(timestamp.st_atime_ns, timestamp.st_mtime_ns))
        self.assertNotEqual(before, resource(self.root))
        path.write_text('original')
        self.assertEqual(before, resource(self.root))

    def test_timestamp_only_is_not_identity(self):
        path = self.root / 'metadata'
        path.write_text('bytes')
        before = resource(path)
        os.utime(path, ns=(0, 0))
        self.assertEqual(before, resource(path))

    def test_symlink_target_bytes_and_link_layout(self):
        target = self.root / 'target'
        target.write_text('alpha')
        link = self.root / 'link'
        link.symlink_to(target)
        first = resource(link)
        target.write_text('bravo')
        self.assertNotEqual(first, resource(link))
        target.write_text('alpha')
        link.unlink()
        link.symlink_to('target')
        self.assertNotEqual(first, resource(link))

    def test_added_removed_and_empty_directories(self):
        first = resource(self.root)
        (self.root / 'empty').mkdir()
        self.assertNotEqual(first, resource(self.root))
        (self.root / 'empty').rmdir()
        self.assertEqual(first, resource(self.root))

    def test_mode_is_identity(self):
        path = self.root / 'metadata'
        path.write_text('bytes')
        before = resource(path)
        path.chmod(0o400)
        self.assertNotEqual(before, resource(path))

    def test_cycles_dangling_links_and_special_files_refused(self):
        cycle = self.root / 'cycle'
        cycle.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'cycle'):
            resource(self.root)
        cycle.unlink()
        cycle.symlink_to(self.root / 'absent')
        with self.assertRaises(FileNotFoundError):
            resource(self.root)
        cycle.unlink()
        os.mkfifo(cycle)
        with self.assertRaisesRegex(ValueError, 'not a regular'):
            resource(self.root)

    def test_alias_refused_before_invoking_binary(self):
        prefix = self.root / 'external'
        Path(str(prefix) + '.nal').write_text('DBLIST untracked_dependency\n')
        with self.assertRaisesRegex(ValueError, 'alias resource closure'):
            blast_database(prefix, '/MUST_NOT_EXECUTE')


if __name__ == '__main__':
    unittest.main()
