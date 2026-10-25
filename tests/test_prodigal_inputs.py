import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('protein_inputs', ROOT/'bin/prepare_prodigal_inputs.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class ProteinInputs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paths = {k: self.root/k for k in ['genome', 'gff', 'proteins', 'cds']}
        self.output = self.root/'output'
        self.paths['genome'].write_text('>ctg_a topology=circular\nATGAAATAA\n>ctg_b\nTTATTTCAT\n')
        self.paths['gff'].write_text(
            '##gff-version  3\n'
            '# Sequence Data: seqnum=1;seqlen=9;seqhdr="ctg_a topology=circular"\n'
            '# Model Data: version=Prodigal.v2.6.3;transl_table=11;uses_sd=1\n'
            'ctg_a\tProdigal_v2.6.3\tCDS\t1\t9\t1\t+\t0\tID=1_1;partial=00;start_type=ATG;\n'
            '# Sequence Data: seqnum=2;seqlen=9;seqhdr="ctg_b"\n'
            '# Model Data: version=Prodigal.v2.6.3;transl_table=4;uses_sd=1\n'
            'ctg_b\tProdigal_v2.6.3\tCDS\t1\t9\t1\t-\t0\tID=2_1;partial=00;start_type=ATG;\n')
        headers = ['ctg_a_1 # 1 # 9 # 1 # ID=1_1;partial=00;start_type=ATG;',
                   'ctg_b_1 # 1 # 9 # -1 # ID=2_1;partial=00;start_type=ATG;']
        for kind, seq in [('proteins', 'MK*'), ('cds', 'ATGAAATAA')]:
            # Out-of-order gene FASTA is restored to source contig order.
            self.paths[kind].write_text(''.join('>'+header+'\n'+seq+'\n' for header in headers[::-1]))

    def prepare(self):
        return adapter.prepare(**self.paths, output=self.output)

    def fail_clean(self, message):
        with self.assertRaisesRegex(ValueError, message): self.prepare()
        self.assertFalse(self.output.exists())

    def test_source_coordinates_strand_ids_order_and_topology(self):
        result = self.prepare()
        self.assertEqual(result['protein_count'], 2)
        self.assertEqual([(x['contig_id'],x['topology']) for x in result['replicons']], [('ctg_a','circular'),('ctg_b','linear')])
        self.assertEqual(result['replicons'][1]['topology_source'], 'unknown_treated_as_linear')
        self.assertEqual((self.output/'replicon_topology.txt').read_text(), 'ctg_a: circular\n')
        proteins = (self.output/'proteins.faa').read_text()
        self.assertLess(proteins.index('>ctg_a_1'), proteins.index('>ctg_b_1'))
        self.assertEqual(proteins.count('MK*'), 2)
        self.assertIn('\t-\t4\t', (self.output/'gene_map.tsv').read_text())
        self.assertEqual(json.loads((self.output/'manifest.json').read_text()), result)

    def test_gzip_magic_and_lowercase_dna_preserve_protein_headers(self):
        original = self.paths['proteins'].read_text()
        for kind,p in self.paths.items():
            data = p.read_bytes()
            if kind == 'genome': data = data.replace(b'ATGAAATAA', b'atgaaataa')
            p.write_bytes(gzip.compress(data, mtime=0))
        self.prepare()
        self.assertEqual(set((self.output/'proteins.faa').read_text().splitlines()), set(original.splitlines()))

    def test_conflicting_circularity_fails_before_outputs(self):
        p=self.paths['genome'];p.write_text(p.read_text().replace('topology=circular','topology=circular circular=false'))
        self.fail_clean('Conflicting topology')

    def test_nucleotide_input_cannot_substitute_for_protein_output(self):
        self.paths['proteins'].write_bytes(self.paths['genome'].read_bytes())
        self.fail_clean('identifiers differ')

    def test_wrong_source_cds_is_not_silently_associated(self):
        p=self.paths['cds'];p.write_text(p.read_text().replace('ATGAAATAA','ATGCCCTAA'))
        self.fail_clean('CDS/source DNA')

    def test_missing_duplicate_genes_and_coordinate_errors_fail(self):
        original=self.paths['proteins'].read_text()
        for bad,diagnostic in [(original+original,'Duplicate ID'),
                               (original.replace(' # 9 # ',' # 6 # '),'coordinate header mismatch'),
                               (original.split('>ctg_a_1')[0],'identifiers differ')]:
            self.paths['proteins'].write_text(bad)
            self.fail_clean(diagnostic)

    def test_zero_genes_retains_contigs_and_explicit_state(self):
        p=self.paths['gff'];p.write_text('\n'.join(l for l in p.read_text().splitlines() if l.startswith('#'))+'\n')
        self.paths['proteins'].write_text('');self.paths['cds'].write_text('')
        result=self.prepare()
        self.assertEqual(result['state'], 'no_predicted_proteins')
        self.assertEqual(result['contig_count'],2)
        self.assertEqual((self.output/'proteins.faa').stat().st_size,0)

    def test_unrepresented_source_contig_is_an_error(self):
        p=self.paths['genome'];p.write_text(p.read_text()+'>missing\nATGAAATAA\n')
        self.fail_clean('Incomplete')

    def test_short_protein_with_only_dna_letters_is_still_valid(self):
        # Protein alphabet heuristics would wrongly reject the peptide ACG.
        for kind,old,new in [('proteins','MK*','ACG'),('cds','ATGAAATAA','GCTTGTGGT'),
                             ('genome','ATGAAATAA','GCTTGTGGT'),('genome','TTATTTCAT','ACCACAAGC')]:
            p=self.paths[kind];p.write_text(p.read_text().replace(old,new))
        self.prepare();self.assertEqual((self.output/'proteins.faa').read_text().count('ACG'),2)


if __name__ == '__main__': unittest.main()
