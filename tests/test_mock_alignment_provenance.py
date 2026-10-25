"""Counterfactuals for mock sample/reference attribution; no native inference claims."""
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests/mock_e2e'))
from generate import generate, SAMPLES

spec = importlib.util.spec_from_file_location('mock_e2e_runner', ROOT / 'tests/mock_e2e/run.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class MockAlignmentProvenance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.fixture = generate(cls.root / 'fixture')
        cls.truth = json.loads((cls.fixture / 'truth.json').read_text())
        cls.bin = cls.root / 'bin'
        cls.bin.mkdir()
        for tool in ['bowtie2-build', 'bowtie2', 'coverm', 'megahit']:
            (cls.bin / tool).write_bytes((ROOT / 'tests/mock_e2e/mock_tool.py').read_bytes())

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.case = Path(tempfile.mkdtemp(dir=self.root))

    def invoke(self, tool, arguments, directory):
        env = dict(os.environ, AUTOPLASM_MOCK_FIXTURE=str(self.fixture), AUTOPLASM_MOCK_PLATFORM='illumina')
        return subprocess.run([sys.executable, str(self.bin / tool), *map(str, arguments)], cwd=directory,
                              env=env, text=True, capture_output=True)

    def alignment(self, reads_sample, reference_sample=None, second_mate_sample=None, slot='aa/111111'):
        directory = self.case / 'work' / slot
        directory.mkdir(parents=True)
        reference_sample = reference_sample or reads_sample
        result = self.invoke('bowtie2-build', ['--threads', '1', self.fixture / reference_sample / 'assembly.fasta', 'index'], directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.invoke('bowtie2', ['-x', 'index', '-1', self.fixture / reads_sample / 'R1.fastq.gz',
                             '-2', self.fixture / (second_mate_sample or reads_sample) / 'R2.fastq.gz'], directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        (directory / 'alignment.bam').write_text(result.stdout)
        return directory, json.loads(result.stdout)

    def trace(self, entries):
        with (self.case / 'trace.tsv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=['hash', 'name'], delimiter='\t')
            writer.writeheader()
            writer.writerows({'hash': slot, 'name': 'ILLUMINA:CONTIG_COVERAGE:BOWTIE2_ALIGN_COVERAGE (' + sid + ')'} for slot, sid in entries)

    def count(self, directory, name):
        result = self.invoke('coverm', ['contig', '--bam-files', directory / 'alignment.bam',
                             '--methods', 'mean', 'tpm', 'rpkm', 'count', '--output-file', name], directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        with (directory / name).open() as stream:
            return list(csv.DictReader(stream, delimiter='\t'))

    def test_each_sample_has_distinguishable_dna_despite_same_contig_ids(self):
        records = [sequence for sample in self.truth['reference_sequences'].values() for sequence in sample.values()]
        self.assertEqual(len(records), 12)
        self.assertEqual(len({hashlib.sha256(value.encode()).hexdigest() for value in records}), 12)
        self.assertTrue(all(set(sample) == {'plasmid_1', 'chromosome_1'} for sample in self.truth['reference_sequences'].values()))

    def test_abundance_does_not_depend_on_output_sample_filename(self):
        directory, payload = self.alignment(SAMPLES[0])
        one = self.count(directory, SAMPLES[0] + '.coverm.tsv')
        self.assertEqual(one, self.count(directory, SAMPLES[1] + '.coverm.tsv'))
        self.assertEqual(one, self.count(directory, 'unrelated-output.tsv'))
        for row in one:
            expected = self.truth['expected_primary_reads'][SAMPLES[0]]['short'][row['Contig']]
            self.assertEqual(int(row['MOCK Read Count']), expected['count'])
        self.assertEqual(len(payload['alignments']), len(payload['input_reads']))

    def test_swapped_reads_are_rejected_even_with_expected_sample_output_name(self):
        directory, _ = self.alignment(SAMPLES[1], reference_sample=SAMPLES[0])
        self.assertTrue(all(int(row['MOCK Read Count']) == 0 for row in self.count(directory, SAMPLES[0] + '.coverm.tsv')))
        self.trace([('aa/111111', SAMPLES[0])])
        with self.assertRaisesRegex(AssertionError, 'sample/read attribution differs'):
            runner.validate_observer_read_provenance(self.case, self.truth)

    def test_swapped_index_is_rejected_even_when_read_ids_are_correct(self):
        directory, _ = self.alignment(SAMPLES[0], reference_sample=SAMPLES[1])
        self.assertTrue(all(int(row['MOCK Read Count']) == 0 for row in self.count(directory, SAMPLES[0] + '.coverm.tsv')))
        self.trace([('aa/111111', SAMPLES[0])])
        with self.assertRaisesRegex(AssertionError, 'index/reference differs'):
            runner.validate_observer_read_provenance(self.case, self.truth)

    def test_mixed_sample_mates_are_not_accepted_as_one_sample(self):
        self.alignment(SAMPLES[0], second_mate_sample=SAMPLES[1])
        self.trace([('aa/111111', SAMPLES[0])])
        with self.assertRaisesRegex(AssertionError, 'sample/read attribution differs'):
            runner.validate_observer_read_provenance(self.case, self.truth)

    def test_out_of_order_task_payloads_keep_sample_attribution(self):
        self.alignment(SAMPLES[1], slot='bb/222222')
        self.alignment(SAMPLES[0], slot='aa/111111')
        self.trace([('aa/111111', SAMPLES[0]), ('bb/222222', SAMPLES[1])])
        self.assertEqual(runner.validate_observer_read_provenance(self.case, self.truth), 2)

    def test_stale_attempt_is_excluded_but_current_evidence_is_mandatory(self):
        self.alignment(SAMPLES[1], reference_sample=SAMPLES[0], slot='zz/999999')
        directory, _ = self.alignment(SAMPLES[0], slot='aa/111111')
        self.trace([('aa/111111', SAMPLES[0])])
        self.assertEqual(runner.validate_observer_read_provenance(self.case, self.truth), 1)
        (directory / 'mock-bowtie2.json').unlink()
        with self.assertRaisesRegex(AssertionError, 'Missing current mapper evidence'):
            runner.validate_observer_read_provenance(self.case, self.truth)

    def test_reference_tampering_after_mapping_cannot_keep_counts(self):
        directory, payload = self.alignment(SAMPLES[0])
        alignment = payload['alignments'][0]
        dna = list(payload['records'][alignment['contig']])
        dna[alignment['start']] = 'C' if dna[alignment['start']] == 'A' else 'A'
        payload['records'][alignment['contig']] = ''.join(dna)
        (directory / 'alignment.bam').write_text(json.dumps(payload))
        result = self.invoke('coverm', ['contig', '--bam-files', directory / 'alignment.bam',
                             '--methods', 'mean', 'count', '--output-file', 'output.tsv'], directory)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Alignment reference differs from actual input read DNA', result.stderr)
        self.assertFalse((directory / 'output.tsv').exists())

    def test_assembler_observer_uses_reads_and_rejects_mixed_samples(self):
        result = self.invoke('megahit', ['-1', self.fixture / SAMPLES[1] / 'R1.fastq.gz',
                             '-2', self.fixture / SAMPLES[1] / 'R2.fastq.gz', '--out-prefix', SAMPLES[0]], self.case)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.case / 'megahit_out' / (SAMPLES[0] + '.contigs.fa')).read_bytes(),
                         (self.fixture / SAMPLES[1] / 'assembly.fasta').read_bytes())
        result = self.invoke('megahit', ['-1', self.fixture / SAMPLES[0] / 'R1.fastq.gz',
                             '-2', self.fixture / SAMPLES[1] / 'R2.fastq.gz', '--out-prefix', 'mixed'], self.case)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('mixed or missing sample reads', result.stderr)


if __name__ == '__main__':
    unittest.main()
