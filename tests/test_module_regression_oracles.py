"""Adversarial exit-status checks for the Nextflow regression runner."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('regressions', Path(__file__).with_name('run_module_regressions.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class NextflowExitOracleTests(unittest.TestCase):
    def invoke(self, returncode, expect_success):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = subprocess.CompletedProcess(['nextflow'], returncode,
                stdout='work-duplicate-keys: duplicate sample key was rejected\n', stderr='')
            with patch.object(runner.subprocess, 'run', return_value=result):
                return runner.run_nf(base, 'unused.nf', base/'fixture', base/'out',
                                     base/'work', base/'trace.tsv', expect_success=expect_success)

    def test_negative_case_rejects_success_even_with_expected_words(self):
        with self.assertRaises(runner.RegressionFailure):
            self.invoke(0, False)

    def test_negative_case_returns_failure_for_diagnostic_checks(self):
        self.assertEqual(self.invoke(1, False).returncode, 1)

    def test_unrelated_failure_with_duplicate_path_is_rejected(self):
        result = subprocess.CompletedProcess([], 1, stdout='work-duplicate-keys: missing input', stderr='')
        with self.assertRaises(runner.RegressionFailure):
            runner.assert_duplicate_join_failure(result)

    def test_real_join_diagnostic_is_accepted_on_either_side(self):
        for side in ('left', 'right'):
            with self.subTest(side=side):
                result = subprocess.CompletedProcess([], 1, stdout='', stderr=
                    f'Detected join operation duplicate emission on {side} channel -- offending element: key=[id:S1]')
                runner.assert_duplicate_join_failure(result)


class QcVersionOracleTests(unittest.TestCase):
    def test_missing_or_unrelated_workdir_rejected_before_output_search(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for record in [{'name': 'MULTIQC (report)'},
                           {'name': 'MULTIQC (report)', 'workdir': str(runner.ROOT)}]:
                with self.subTest(record=record), \
                     patch.object(runner, 'trace_rows', return_value=[record]), \
                     self.assertRaises(runner.RegressionFailure):
                    runner.multiqc_data_text(base / 'work', base / 'trace')

    def invoke_qc(self, multiqc_output, code=0):
        def result(command, **kwargs):
            output = {'fastqc': 'FastQC v0.13.0\n', 'fastp': 'fastp 1.3.6\n'}.get(command[0], multiqc_output)
            status = 0 if command[0] == 'fastqc' else code
            return subprocess.CompletedProcess(command, status, stdout=output, stderr='')
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(runner.shutil, 'which', side_effect=lambda name: '/declared/bin/' + name), \
             patch.object(runner.subprocess, 'run', side_effect=result), \
             patch.object(runner, 'run_nf', side_effect=AssertionError('analysis must not start')):
            runner.suite_qc(Path(directory))

    def test_wrong_multiqc_rejected_before_any_analysis(self):
        for output in ['multiqc, version 1.33\n', 'multiqc, version 1.350\n',
                       'multiqc, version 1.35.dev1\n', 'unrelated banner 1.35\n']:
            with self.subTest(output=output), self.assertRaises(runner.RegressionFailure):
                self.invoke_qc(output)

    def test_failed_version_command_rejected_even_with_correct_text(self):
        with self.assertRaises(runner.RegressionFailure):
            self.invoke_qc('multiqc, version 1.35\n', code=1)

    def test_declared_versions_are_recorded_on_correct_success(self):
        outputs = [subprocess.CompletedProcess([], 0, stdout='FastQC v0.13.0\n', stderr=''),
                   subprocess.CompletedProcess([], 0, stdout='multiqc, version 1.35\n', stderr=''),
                   subprocess.CompletedProcess([], 0, stdout='', stderr='fastp 1.3.6\n')]
        with patch.object(runner.subprocess, 'run', side_effect=outputs), \
             patch.object(runner.shutil, 'which', side_effect=lambda name: '/declared/bin/' + name):
            versions = runner.require_qc_versions()
        self.assertEqual(versions['multiqc']['actual'], '1.35')
        self.assertEqual(versions['fastqc']['actual'], '0.13.0')
        self.assertEqual(versions['multiqc']['expected'], '1.35')


if __name__ == '__main__':
    unittest.main()
