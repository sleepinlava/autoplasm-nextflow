"""Check double naming against fixed Bowtie2 wrapper and native output controls.

All reads are intentionally passed through by this observer; no mapping inference.
"""
import gzip
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MOCK = ROOT / 'tests/mock_e2e/mock_tool.py'


class MockBowtieUnalignedTests(unittest.TestCase):
    def check_names(self, template, expected):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / 'bowtie2').write_bytes(MOCK.read_bytes())
            (base / 'index.mock.json').write_text(json.dumps({'reference': 'ACGT'}))
            reads = ['@r/1\nACGT\n+\n!~#%\n', '@r/2\nTGCA\n+\n$%&*\n']
            for mate, data in enumerate(reads, 1):
                (base / f'R{mate}.fastq').write_text(data)
            env = os.environ.copy(); env['AUTOPLASM_MOCK_FIXTURE'] = str(base)
            result = subprocess.run(['python3', str(base / 'bowtie2'), '-x', 'index',
                '-1', 'R1.fastq', '-2', 'R2.fastq', '--un-conc-gz', template],
                cwd=base, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            outputs = sorted(p.name for p in base.iterdir()
                             if p.name not in {'bowtie2', 'index.mock.json', 'R1.fastq', 'R2.fastq', 'mock-bowtie2.json'})
            self.assertEqual(outputs, sorted(expected))
            for name, data in zip(expected, reads):
                with gzip.open(base / name, 'rt') as stream:
                    self.assertEqual(stream.read(), data)

    def test_final_extension(self):
        self.check_names('sample.unmapped.fastq.gz',
                         ['sample.unmapped.fastq.1.gz', 'sample.unmapped.fastq.2.gz'])

    def test_placeholder(self):
        self.check_names('sample.%.fastq.gz', ['sample.1.fastq.gz', 'sample.2.fastq.gz'])

    def test_no_extension(self):
        self.check_names('unmapped', ['unmapped.1', 'unmapped.2'])


if __name__ == '__main__':
    unittest.main()
