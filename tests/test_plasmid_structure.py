"""Header interpretation regressions; synthetic sequence is not topology truth."""
import csv
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StructureHeaderTests(unittest.TestCase):
    def run_headers(self, headers, repeat=False):
        rng = random.Random(20261020)
        sequence = ''.join(rng.choice('ACGT') for _ in range(500))
        if repeat:
            sequence += sequence[:25]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            fasta, table = base/'input.fasta', base/'structure.tsv'
            fasta.write_text(''.join(f'>{header}\n{sequence}\n' for header in headers))
            result = subprocess.run(['Rscript', str(ROOT/'bin/plasmid_structure.R'),
                '--contigs', str(fasta), '--sample-id', 'S1', '--out', str(table)],
                text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with table.open() as handle:
                return list(csv.DictReader(handle, delimiter='\t'))

    def test_explicit_negative_headers_are_not_positive_markers(self):
        headers = ['p0 not_circular', 'p1_not_circular', 'p2 circular=false',
                   'p3 topology=linear', 'p4_circular circular=false']
        for row in self.run_headers(headers):
            with self.subTest(plasmid=row['plasmid_id']):
                self.assertEqual((row['is_circular'], row['method'], row['terminal_overlap_bp']),
                                 ('false', 'none', '0'))

    def test_supported_positive_markers_remain_supported(self):
        for row in self.run_headers(['p0 circular=true', 'p1 topology=circular',
                                     'p2_circular', 'p3 CIRCULAR=TRUE']):
            self.assertEqual((row['is_circular'], row['method']), ('true', 'header_marker'))

    def test_partial_or_embedded_markers_do_not_match(self):
        for row in self.run_headers(['p0 circular=trueish', 'p1 topology=circularity',
                'p2_circular_extra', 'p3 description=circular=true', 'p4 notes_circular_text']):
            self.assertEqual((row['is_circular'], row['method']), ('false', 'none'))

    def test_conflicting_header_markers_disable_header_inference(self):
        for row in self.run_headers(['p0 circular=true circular=false',
                                     'p1_circular topology=linear']):
            self.assertEqual(row['is_circular'], 'false')
            self.assertIn('conflicting circularity header markers', row['warnings'])

    def test_negative_header_does_not_suppress_independent_dtr(self):
        row = self.run_headers(['p0 circular=false'], repeat=True)[0]
        self.assertEqual((row['is_circular'], row['method'], row['terminal_overlap_bp']),
                         ('true', 'dtr', '25'))


class StructureTopologyTests(unittest.TestCase):
    """Sequence geometry controls, not synthetic claims of molecular topology."""
    def run_sequences(self, records):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, output = base / 'input.fasta', base / 'structure.tsv'
            source.write_text(''.join('>' + name + '\n' + dna + '\n' for name, dna in records))
            result = subprocess.run(['Rscript', str(ROOT / 'bin/plasmid_structure.R'),
                                     '--contigs', str(source), '--sample-id', 'S1', '--out', str(output)],
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with output.open() as stream:
                reader = csv.DictReader(stream, delimiter='\t')
                rows = list(reader)
                fields = reader.fieldnames
            self.assertEqual([row['plasmid_id'] for row in rows], [name.split()[0] for name, _ in records])
            self.assertTrue(all(row['sample_id'] == 'S1' for row in rows))
            self.assertEqual([int(row['length_bp']) for row in rows], [len(dna) for _, dna in records])
            return rows, fields

    @staticmethod
    def sequence(itr=0, dtr=0):
        rng = random.Random(3661)
        head = ''.join(rng.choices('ACGT', k=itr or dtr or 30))
        body = 'A' + ''.join(rng.choices('ACGT', k=798)) + 'A'
        tail = head.translate(str.maketrans('ACGT', 'TGCA'))[::-1] if itr else (head if dtr else ''.join(rng.choices('ACGT', k=len(head))))
        return head + body + tail

    def test_itr_only_is_structural_evidence_and_unknown_topology(self):
        row = self.run_sequences([('itr', self.sequence(itr=25))])[0][0]
        self.assertEqual((row['is_circular'], row['method'], row['terminal_overlap_bp']), ('false', 'itr', '25'))
        self.assertEqual((row['repeat_type'], row['topology_status'], row['topology_evidence']), ('itr', 'unknown', 'none'))
        self.assertIn('not confirmed linear', row['warnings'])

    def test_header_can_support_a_candidate_independently_of_itr(self):
        row = self.run_sequences([('itr topology=circular', self.sequence(itr=25))])[0][0]
        self.assertEqual((row['is_circular'], row['method'], row['repeat_type']), ('true', 'header_marker', 'itr'))
        self.assertEqual((row['topology_status'], row['topology_evidence']), ('circular_candidate', 'header_marker'))

    def test_dtr_candidate_is_preserved(self):
        row = self.run_sequences([('dtr', self.sequence(dtr=25))])[0][0]
        self.assertEqual((row['is_circular'], row['method'], row['repeat_type']), ('true', 'dtr', 'dtr'))
        self.assertEqual((row['topology_status'], row['topology_evidence']), ('circular_candidate', 'dtr'))

    def test_absence_of_repeat_does_not_claim_linearity(self):
        row = self.run_sequences([('no_repeat', self.sequence())])[0][0]
        self.assertEqual((row['is_circular'], row['method'], row['repeat_type'], row['topology_status']), ('false', 'none', 'none', 'unknown'))

    def test_low_complexity_itr_is_still_filtered(self):
        body = self.sequence()[30:-30]
        row = self.run_sequences([('low_complexity', 'A' * 30 + body + 'T' * 30)])[0][0]
        self.assertEqual((row['is_circular'], row['method'], row['repeat_type']), ('false', 'none', 'none'))
        self.assertEqual(row['topology_status'], 'unknown')
        self.assertIn('low-complexity terminal repeat filtered', row['warnings'])

    def test_itr_seed_and_length_limit_are_unchanged(self):
        rows = self.run_sequences([('short', self.sequence(itr=20)), ('seed', self.sequence(itr=21)), ('long', self.sequence(itr=1001))])[0]
        self.assertEqual([(row['is_circular'], row['method'], row['terminal_overlap_bp']) for row in rows], [('false', 'none', '0'), ('false', 'itr', '21'), ('false', 'itr', '1000')])

    def test_dtr_and_itr_are_not_collapsed_to_one_repeat_type(self):
        half = 'ACGTCAGTACG'
        palindrome = half + half.translate(str.maketrans('ACGT', 'TGCA'))[::-1]
        row = self.run_sequences([('both', palindrome + self.sequence()[30:-30] + palindrome)])[0][0]
        self.assertEqual((row['is_circular'], row['method'], row['repeat_type']), ('true', 'dtr', 'dtr+itr'))
        self.assertEqual(row['topology_evidence'], 'dtr')

    def test_empty_input_keeps_legacy_columns_and_new_schema(self):
        rows, fields = self.run_sequences([])
        self.assertEqual(rows, [])
        self.assertEqual(fields, ['sample_id', 'plasmid_id', 'length_bp', 'is_circular', 'terminal_overlap_bp', 'method', 'warnings', 'source_file', 'repeat_type', 'topology_status', 'topology_evidence'])


if __name__ == '__main__':
    unittest.main()
