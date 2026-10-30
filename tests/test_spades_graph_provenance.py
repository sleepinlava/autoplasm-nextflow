"""Final-copy provenance expectations independent of a directory-name maximum."""
from pathlib import Path
import importlib.util
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'bin/spades_graph_provenance.py'
spec = importlib.util.spec_from_file_location('spades_graph_provenance', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'K33/assembly_graph.fastg'
        self.source.parent.mkdir()
        self.source.write_text('>EDGE_1;\nACGT\n')
        self.config = self.root / 'K33/configs/config.info'
        self.config.parent.mkdir()
        self.config.write_text('K 33\nmain_iteration true\n')
        self.target = self.root / 'assembly_graph.fastg'
        self.target.write_bytes(self.source.read_bytes())
        self.export = self.root / 'sample.assembly_graph.fastg'
        self.export.write_bytes(self.source.read_bytes())
        self.log = self.root / 'spades.log'
        self.log.write_text('===== K33 finished.\n===== Copy files finished.\n'
                            '======= SPAdes pipeline finished.\n')
        self.plan = [{'short_name': 'copy_files', 'args': [
            '/spades/copy_files.py', str(self.source), str(self.target)]}]

    def collect(self):
        return module.collect(self.root, self.export, self.log, self.plan)

    def test_actual_copy_ignores_unrelated_higher_directory(self):
        (self.root / 'K127').mkdir()
        self.assertEqual(self.collect()['max_k'], 33)
        self.assertEqual(self.collect()['copy_source'], 'K33/assembly_graph.fastg')

    def test_warning_completion_retains_emitted_warnings_without_summary(self):
        message = '0:00:01  1M WARN General (model.cpp : 12) Threshold set to: 0'
        self.log.write_text(message + '\n' + message + '\n'
                            '== Warning == Unrecognized warning remains visible\n'
                            '===== K33 finished. \n===== Copy files finished. \n'
                            '======= SPAdes pipeline finished WITH WARNINGS!\n'
                            ' * ' + message + '\n')
        result = self.collect()
        self.assertTrue(result['completed_with_warnings'])
        self.assertEqual(result['warnings_count'], 3)
        self.assertEqual(result['warnings'], [message, message,
                         '== Warning == Unrecognized warning remains visible'])
        self.assertEqual(result['warning_count_unit'], 'emitted_lines_excluding_summary')

    def test_abnormal_completion_is_not_success(self):
        self.log.write_text(self.log.read_text().replace(
            '======= SPAdes pipeline finished.',
            '======= SPAdes pipeline finished abnormally and WITH WARNINGS!'))
        with self.assertRaisesRegex(ValueError, 'completion marker'):
            self.collect()

    def test_old_success_cannot_mask_later_abnormal_completion(self):
        self.log.write_text(self.log.read_text() +
                            '======= SPAdes pipeline finished abnormally and WITH WARNINGS!\n')
        with self.assertRaisesRegex(ValueError, 'completion marker'):
            self.collect()

    def test_old_success_cannot_mask_incomplete_new_invocation(self):
        self.log.write_text(self.log.read_text() +
                            '======= SPAdes pipeline started. Log can be found here: spades.log\n')
        with self.assertRaisesRegex(ValueError, 'completion marker'):
            self.collect()

    def test_completion_markers_must_be_lines_in_execution_order(self):
        for text in [
            'example: ===== K33 finished.\n===== Copy files finished.\n======= SPAdes pipeline finished.\n',
            '===== K33 finished.\n===== Copy files finished.\n======= SPAdes pipeline finished.not really\n',
            '===== Copy files finished.\n===== K33 finished.\n======= SPAdes pipeline finished.\n',
        ]:
            with self.subTest(text=text):
                self.log.write_text(text)
                with self.assertRaisesRegex(ValueError, 'completion marker'):
                    self.collect()

    def test_latest_invocation_controls_warning_state(self):
        self.log.write_text(self.log.read_text() +
                            '======= SPAdes pipeline started. Log can be found here: spades.log\n'
                            '===== K33 finished.\n===== Copy files finished.\n'
                            '======= SPAdes pipeline finished WITH WARNINGS!\n')
        self.assertTrue(self.collect()['completed_with_warnings'])

    def test_graph_mismatch_rejected(self):
        self.export.write_text('>EDGE_1;\nTGCA\n')
        with self.assertRaisesRegex(ValueError, 'bytes mismatch'):
            self.collect()

    def test_config_k_mismatch_rejected(self):
        self.config.write_text('K 55\nmain_iteration true\n')
        with self.assertRaisesRegex(ValueError, 'K/config mismatch'):
            self.collect()

    def test_non_main_iteration_rejected(self):
        self.config.write_text('K 33\nmain_iteration false\n')
        with self.assertRaisesRegex(ValueError, 'not the main iteration'):
            self.collect()

    def test_incomplete_assembly_rejected(self):
        self.log.write_text('===== K33 finished.\n')
        with self.assertRaisesRegex(ValueError, 'completion marker'):
            self.collect()

    def test_duplicate_copy_stage_rejected(self):
        self.plan *= 2
        with self.assertRaisesRegex(ValueError, 'one final copy_files'):
            self.collect()

    def test_foreign_source_rejected(self):
        self.plan[0]['args'][1] = str(self.root / 'foreign/K33/assembly_graph.fastg')
        with self.assertRaisesRegex(ValueError, 'not this assembly K directory'):
            self.collect()

    def test_duplicate_final_graph_copy_rejected(self):
        self.plan[0]['args'] += [str(self.source), str(self.target)]
        with self.assertRaisesRegex(ValueError, 'one final FASTG copy'):
            self.collect()


if __name__ == '__main__':
    unittest.main()
