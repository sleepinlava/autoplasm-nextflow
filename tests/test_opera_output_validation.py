"""OPERA-MS fatal child diagnostics cannot be accepted as successful assembly."""
from pathlib import Path
import importlib.util
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'bin/validate_opera_ms_output.py'
spec=importlib.util.spec_from_file_location('opera_validation',SOURCE)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class OutputValidation(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out=Path(self.temp.name)
        self.coverage=self.out/module.REQUIRED
        self.coverage.parent.mkdir(parents=True)
        self.coverage.touch()
        (self.out/'contigs.fasta').write_text('>final\nACGT\n')

    def test_normal_warning_and_error_rate_are_not_fatal(self):
        self.coverage.write_text('Loading contigs ...\nAnalyzing 1 library\n')
        (self.out/'gap.log').write_text('xargs: warning: options --max-lines and --replace are mutually exclusive\nerror rate: 0.03\n')
        self.assertEqual(module.validate(self.out),2)

    def test_real_samtools_assertion_invalidates_existing_final(self):
        self.coverage.write_text("samtools: bgzf.c:142: bgzf_open: Assertion `compressBound(0xff00) < 0x10000' failed.\n")
        with self.assertRaisesRegex(ValueError,'internal process failure'):
            module.validate(self.out)
        self.assertTrue((self.out/'contigs.fasta').exists())

    def test_core_dump_in_nested_log_invalidates_existing_final(self):
        log=self.out/'gap/stage/consensus_cmd.sh.log'
        log.parent.mkdir(parents=True)
        log.write_text('/bin/sh: line 1: 1442 Segmentation fault (core dumped) racon\n')
        with self.assertRaisesRegex(ValueError,'gap/stage/consensus_cmd.sh.log:1'):
            module.validate(self.out)

    def test_aborted_child_is_fatal(self):
        self.coverage.write_text('Aborted (core dumped)\n')
        with self.assertRaisesRegex(ValueError,'internal process failure'):
            module.validate(self.out)

    def test_missing_dynamic_library_is_fatal(self):
        self.coverage.write_text('samtools: error while loading shared libraries: libncurses.so.5: cannot open shared object file\n')
        with self.assertRaisesRegex(ValueError,'internal process failure'):
            module.validate(self.out)

    def test_missing_executable_is_fatal(self):
        for message in ['sh: samtools: command not found', 'Can\'t exec "samtools": No such file or directory']:
            with self.subTest(message=message):
                self.coverage.write_text(message+'\n')
                with self.assertRaisesRegex(ValueError,'internal process failure'):
                    module.validate(self.out)

    def test_missing_coverage_diagnostic_is_not_empty_success(self):
        self.coverage.unlink()
        with self.assertRaisesRegex(ValueError,'coverage diagnostic missing'):
            module.validate(self.out)

    def test_symlink_diagnostic_is_not_trusted(self):
        self.coverage.unlink()
        self.coverage.symlink_to(self.out/'contigs.fasta')
        with self.assertRaisesRegex(ValueError,'not a regular file'):
            module.validate(self.out)
        self.coverage.unlink()
        self.coverage.touch()
        (self.out/'other.err').symlink_to(self.out/'contigs.fasta')
        with self.assertRaisesRegex(ValueError,'diagnostic is a symlink'):
            module.validate(self.out)


if __name__=='__main__':
    unittest.main()
