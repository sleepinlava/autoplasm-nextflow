"""Input identity and product-transport cases, using explicit synthetic DNA."""
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('plasmaag_inputs', ROOT / 'bin/plasmaag_inputs.py')
MODULE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)


class PlasMAAGInputs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name); self.rows = []
        for i, name in enumerate(['A.1', 'A__1']):
            bundle = self.base / ('spades' + str(i)); bundle.mkdir()
            dna = ('ACGT' if i == 0 else 'TGCA') * 600
            (bundle / 'contigs.fasta').write_text('>shared local contig description\n' + dna + '\n')
            (bundle / 'contigs.paths').write_text('shared\n1+\n')
            (bundle / 'assembly_graph_after_simplification.gfa').write_text('S\t1\t' + dna + '\tKC:i:5000\n')
            reads = []
            for pair in [1, 2]:
                path = self.base / f'{i}_{pair}.fq'; path.write_text('@pair\nACGT\n+\nIIII\n'); reads.append(str(path))
            self.rows.append(dict(meta=dict(id=name, group='group' + str(i)), reads=reads, assembly=str(bundle)))

    def prepare(self, rows=None, assembler='metaspades', name='prepared'):
        path = self.base / (name + '.json')
        path.write_text(json.dumps(dict(assembler=assembler, records=self.rows if rows is None else rows)))
        output = self.base / name
        return MODULE.prepare(path, output), output

    def native(self, state, source):
        result = self.base / 'native'; result.mkdir()
        for category in ['candidate_plasmids', 'candidate_genomes', 'candidate_virus']:
            (result / category).mkdir()
            (result / (category + '.tsv')).write_text('clustername\tcontigname\n')
        # Same local ID, distinct original DNA, one plasmid / one short genome.
        (result / 'candidate_plasmids.tsv').write_text('clustername\tcontigname\nS0C7_plas\tS0Cshared\n')
        (result / 'candidate_genomes.tsv').write_text('clustername\tcontigname\nS1C8_org\tS1Cshared\n')
        (result / 'candidate_plasmids/S0C7_plas.fna').write_text('>S0Cshared\n' + 'ACGT' * 600 + '\n')
        for name in ['plasmid_scores.tsv', 'virus_genomes_scores.tsv']:
            (result / name).write_text('clustername\tchromosome_score\tplasmid_score\tvirus_score\n' + ('S0C7_plas\t0.01\t0.98\t0.01\n' if name == 'plasmid_scores.tsv' else 'S1C8_org\t0.99\t0.005\t0.005\n'))
        return result

    def test_reverse_arrival_order_restores_metadata_and_original_ids(self):
        state, output = self.prepare(list(reversed(self.rows)))
        self.assertEqual([r['meta']['id'] for r in state['samples']], ['A.1', 'A__1'])
        native = self.native(state, output)
        exported = self.base / 'validated'
        manifest = MODULE.validate(output / 'sample-map.json', native, exported)
        self.assertEqual([(s['meta'], s['bins'], s['state']) for s in manifest['samples']],
                         [(self.rows[0]['meta'], 1, 'candidate_plasmid_bins'), (self.rows[1]['meta'], 0, 'no_candidate_plasmid_bins')])
        first = exported / manifest['samples'][0]['relative_directory'] / 'S0C7_plas.fna'
        self.assertEqual(first.read_text(), '>shared\n' + 'ACGT' * 600 + '\n')
        self.assertNotEqual(manifest['samples'][0]['relative_directory'], manifest['samples'][1]['relative_directory'])
        self.assertFalse(list((exported / 'native_results/candidate_genomes').glob('*.fna')))

    def test_duplicate_ids_rejected_before_manifest(self):
        self.rows[1]['meta']['id'] = self.rows[0]['meta']['id']
        with self.assertRaisesRegex(ValueError, 'unique nonempty'): self.prepare()
        self.assertFalse((self.base / 'prepared').exists())

    def test_reused_reads_rejected(self):
        self.rows[1]['reads'][0] = self.rows[0]['reads'][0]
        with self.assertRaisesRegex(ValueError, 'assigned more than once'): self.prepare()

    def test_missing_spades_paths_rejected(self):
        (Path(self.rows[0]['assembly']) / 'contigs.paths').unlink()
        with self.assertRaisesRegex(ValueError, 'bundle missing: contigs.paths'): self.prepare()

    def test_megahit_gzip_full_dna_is_not_positive_filtered(self):
        rows = []
        for i, row in enumerate(self.rows):
            source = self.base / f'{i}.fa.gz'
            source.write_bytes(gzip.compress(('>shared details\n' + ('ACGT' if i == 0 else 'TGCA') * 600 + '\n').encode()))
            rows.append(dict(row, assembly=str(source)))
        state, output = self.prepare(rows, assembler='megahit')
        self.assertEqual((output / 'reads-and-assembly.tsv').read_text().splitlines()[0], 'read1\tread2\tcontigs')
        self.assertEqual((output / 'sample_1/contigs.fasta').read_text(), '>shared\n' + 'TGCA' * 600 + '\n')
        self.assertEqual([s['contigs'] for s in state['samples']], [1, 1])

    def test_mismatched_final_dna_rejected(self):
        state, output = self.prepare(); native = self.native(state, output)
        path = native / 'candidate_plasmids/S0C7_plas.fna'
        path.write_text(path.read_text().replace('ACGT', 'TGCA'))
        with self.assertRaisesRegex(ValueError, 'DNA differs'): MODULE.validate(output / 'sample-map.json', native, self.base / 'export')

    def test_missing_membership_rejected(self):
        state, output = self.prepare(); native = self.native(state, output)
        (native / 'candidate_plasmids.tsv').write_text('clustername\tcontigname\n')
        with self.assertRaisesRegex(ValueError, 'final bin set differs'): MODULE.validate(output / 'sample-map.json', native, self.base / 'export')

    def test_nan_score_rejected(self):
        state, output = self.prepare(); native = self.native(state, output)
        path = native / 'plasmid_scores.tsv'; path.write_text(path.read_text().replace('0.98', 'nan'))
        with self.assertRaisesRegex(ValueError, 'Invalid native PlasMAAG score'): MODULE.validate(output / 'sample-map.json', native, self.base / 'export')


if __name__ == '__main__': unittest.main()
