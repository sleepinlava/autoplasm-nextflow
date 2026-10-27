"""Native parser/read-set controls; fake GTDB files never certify classification."""
import importlib.util
import logging
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('semibin_resource_test', ROOT / 'bin/semibin_runtime_resources.py')
resolver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolver)


class RuntimeResources(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.fasta = self.root / 'input.fna'
        self.bam = self.root / 'input.bam'
        self.fasta.write_bytes(b'>READ_SET_ONLY\nACGT\n')
        self.bam.write_bytes(b'EXPLICIT_READ_SET_OBSERVER_NOT_BAM\n')
        self.args = ['single_easy_bin', '--input-fasta', str(self.fasta),
                     '--input-bam', str(self.bam), '--output', 'sample']

    def tearDown(self):
        self.directory.cleanup()

    def capture(self, *args):
        return resolver.capture({'scope': 'EXPLICIT_PARSER_READ_SET_CONTROL'}, self.args + list(args))

    def test_default_self_training_uses_marker_and_code(self):
        value = self.capture()
        self.assertEqual(value['parsed_arguments']['training_type'], 'self')
        self.assertIn('bundled_marker', value['resources'])
        self.assertIn('main.py', value['resources']['package_code'])
        self.assertNotIn('pretrained_model', value['resources'])
        self.assertNotIn('gtdb_reference_directory', value['resources'])

    def test_native_environment_alias_resolves_real_bundled_model(self):
        value = self.capture('--environment', 'human-gut')
        from SemiBin.utils import get_model_path
        expected = resolver.resource(get_model_path('human_gut'))
        self.assertEqual(value['resources']['pretrained_model'], expected)
        self.assertGreater(expected[0]['bytes'], 0)

    def test_semi_with_precomputed_taxonomy_bypasses_gtdb(self):
        tax = self.root / 'taxonomy.tsv'
        tax.write_text('EXPLICIT_READ_SET_ONLY\n')
        value = self.capture('--semi-supervised', '--taxonomy-annotation-table', str(tax))
        self.assertEqual(value['parsed_arguments']['training_type'], 'semi')
        self.assertEqual(value['resources']['taxonomy_results_fname'], [resolver.resource(tax)])
        self.assertNotIn('gtdb_reference_directory', value['resources'])

    def test_gtdb_prefix_sidecars_and_hidden_newline_member(self):
        ref = self.root / 'gtdb'
        ref.mkdir()
        (ref / 'GTDB').write_bytes(b'FAKE_PREFIX_NOT_A_DATABASE')
        sidecar = ref / '.hidden\nsidecar'
        sidecar.write_bytes(b'old\n')
        old_stat = sidecar.stat()
        first = self.capture('--semi-supervised', '--reference-db', str(ref))
        sidecar.write_bytes(b'new\n')
        os.utime(sidecar, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns))
        second = self.capture('--semi-supervised', '--reference-db', str(ref))
        self.assertNotEqual(first['resources']['gtdb_reference_directory'], second['resources']['gtdb_reference_directory'])

    def test_missing_gtdb_refuses_instead_of_unfingerprinted_download(self):
        with self.assertRaisesRegex(ValueError, 'Prepare the selected SemiBin GTDB'):
            self.capture('--semi-supervised', '--reference-db', str(self.root / 'missing'))

    def test_native_both_training_flags_keep_self_training(self):
        value = self.capture('--semi-supervised', '--self-supervised')
        self.assertEqual(value['parsed_arguments']['training_type'], 'self')
        self.assertNotIn('gtdb_reference_directory', value['resources'])

    def test_external_protein_override_is_hashed(self):
        proteins = self.root / 'genes.faa'
        proteins.write_bytes(b'>READ_SET_ONLY\nAAA\n')
        value = self.capture('--prodigal-output-faa', str(proteins))
        self.assertEqual(value['resources']['prodigal_output_faa'], [resolver.resource(proteins)])

    def test_directory_failures_and_link_target_are_explicit(self):
        ref = self.root / 'ref'
        ref.mkdir()
        target = self.root / 'target'
        target.write_bytes(b'bytes')
        link = ref / 'link'
        link.symlink_to(target)
        self.assertEqual(resolver.resource(ref)[1]['link'], str(target))
        target.unlink()
        with self.assertRaises(FileNotFoundError):
            resolver.resource(ref)
        link.unlink()
        (ref / 'loop').symlink_to(ref, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'cycle'):
            resolver.resource(ref)
        (ref / 'loop').unlink()
        os.mkfifo(ref / 'fifo')
        with self.assertRaisesRegex(ValueError, 'not regular'):
            resolver.resource(ref)


if __name__ == '__main__':
    logging.disable(logging.WARNING)
    unittest.main()
