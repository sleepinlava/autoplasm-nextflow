"""The unpaired fixture double must respect -0 in every output mode."""
import gzip
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MOCK = ROOT / 'tests/mock_e2e/mock_tool.py'


class MockSamtoolsFastqTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.data = '@unpaired\nACGT\n+\n!~#%\n'
        (self.base / 'input.fastq').write_text(self.data)
        self.script = self.base / 'samtools'
        self.script.write_bytes(MOCK.read_bytes())

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, separate=False, unpaired=True):
        bam = self.base / 'input.bam'
        bam.write_text(json.dumps({'mock': True, 'format': 'bam', 'unpaired': unpaired,
                                   'fastq': str(self.base / 'input.fastq')}))
        args = ['fastq', '-0', 'other.fastq.gz', str(bam)]
        if separate: args += ['-1', 'one.fastq.gz', '-2', 'two.fastq.gz', '-s', 'single.fastq.gz']
        env = os.environ.copy(); env['AUTOPLASM_MOCK_FIXTURE'] = str(self.base)
        return subprocess.run(['python3', str(self.script), *args], cwd=self.base, env=env, capture_output=True, text=True)

    def test_interleaving_does_not_move_category_zero_to_stdout(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '')
        self.assertTrue((self.base / 'other.fastq.gz').is_file())
        with gzip.open(self.base / 'other.fastq.gz', 'rt') as stream:
            self.assertEqual(stream.read(), self.data)

    def test_separate_outputs_keep_category_zero_and_empty_pair_files(self):
        result = self.invoke(separate=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '')
        for name in ['one', 'two', 'single']:
            self.assertTrue((self.base / (name + '.fastq.gz')).is_file())
            with gzip.open(self.base / (name + '.fastq.gz'), 'rt') as stream:
                self.assertEqual(stream.read(), '')
        with gzip.open(self.base / 'other.fastq.gz', 'rt') as stream:
            self.assertEqual(stream.read(), self.data)

    def test_unmodeled_paired_input_is_rejected_instead_of_fabricated(self):
        result = self.invoke(unpaired=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unpaired long-read records only', result.stderr)


if __name__ == '__main__':
    unittest.main()
