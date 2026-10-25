"""Identity, missing evidence, and failure controls for per-sample PlasX inputs."""
import gzip
import importlib.util
from pathlib import Path
import subprocess
import multiprocessing
import sqlite3
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'bin' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


px = module('plasx_inputs')
checked = module('plasx_checked')
anvio_checked = module('anvio_checked')


class PlasXInputs(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.assembly = self.base / 'assembly.fa'
        self.assembly.write_text('>original|1 description\nATGAAATAA\n>original.2\nATGAAATAA\n>no_genes\nACGT\n')
        self.prefix = self.base / 'S.1'
        px.prepare(self.assembly, 'S.1', self.prefix)
        self.mapping, self.sequences = px.load_mapping(str(self.prefix) + '.id_map.tsv', str(self.prefix) + '.contigs.fasta', 'S.1')
        self.keys = list(self.mapping)
        self.gene_path = self.base / 'genes.tsv'
        columns = ['gene_callers_id', 'contig', 'start', 'stop', 'direction', 'source', 'version', 'aa_sequence']
        px.write_table(self.gene_path, columns, [dict(zip(columns, [str(i), self.keys[i], '0', '9', 'f', 'prodigal', 'v2.6.3', 'MK'])) for i in range(2)])
        self.genes = px.load_genes(self.gene_path, self.sequences)
        self.annotations = self.base / 'annotations.tsv'
        self.annotations.write_text('gene_callers_id\tsource\taccession\te_value\n0\tPfam\tPF00001.2\t1e-20\n')
        self.denovo = self.base / 'denovo.tsv'
        self.denovo.write_text('gene_callers_id\tcontig\tstart\tstop\tdirection\te_value\taccession\n')
        self.scores = self.base / 'scores.tsv'
        self.scores.write_text('contig\tscore\n' + self.keys[0] + '\t0.90000000000000002\n')

    def finish(self):
        return px.finalize(self.scores, self.mapping, self.sequences, self.genes, self.annotations, self.denovo,
                           self.base / 'output.tsv', self.base / 'states.tsv', 'S.1')

    def test_original_ids_probabilities_and_missing_evidence(self):
        result = self.finish()
        self.assertEqual((self.base / 'output.tsv').read_text(), 'contig\tscore\noriginal|1\t0.90000000000000002\n')
        self.assertEqual(result['scored_contigs'], 1)
        states = px.table(self.base / 'states.tsv', ['contig', 'status'])
        self.assertEqual([r['status'] for r in states], ['scored', 'not_assessed_no_annotations', 'not_assessed_no_genes'])

    def test_compressed_input_and_duplicate_identifiers(self):
        compressed = self.base / 'assembly.GZ'
        with gzip.open(compressed, 'wb') as stream:
            stream.write(self.assembly.read_bytes())
        px.prepare(compressed, 'S.1', self.base / 'compressed')
        self.assertEqual((self.base / 'compressed.contigs.fasta').read_bytes(), Path(str(self.prefix) + '.contigs.fasta').read_bytes())
        self.assembly.write_text('>duplicate\nACGT\n>duplicate\nTGCA\n')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            px.prepare(self.assembly, 'S.1', self.base / 'duplicate')

    def test_same_gene_numbers_from_another_sample_are_rejected(self):
        px.prepare(self.assembly, 'S.2', self.base / 'S.2')
        other, sequences = px.load_mapping(self.base / 'S.2.id_map.tsv', self.base / 'S.2.contigs.fasta', 'S.2')
        self.assertTrue(set(other).isdisjoint(self.mapping))
        with self.assertRaisesRegex(ValueError, 'foreign gene'):
            px.load_genes(self.gene_path, sequences)
        with self.assertRaisesRegex(ValueError, 'this sample'):
            px.load_mapping(str(self.prefix) + '.id_map.tsv', str(self.prefix) + '.contigs.fasta', 'S.2')

    def test_foreign_annotations_with_valid_local_gene_numbers_fail_db_comparison(self):
        database = self.base / 'sample.db'
        with sqlite3.connect(database) as connection:
            connection.executescript('CREATE TABLE self(key TEXT,value TEXT); CREATE TABLE contig_sequences(contig TEXT,sequence TEXT); '
                                     'CREATE TABLE genes_in_contigs(gene_callers_id INT,contig TEXT,start INT,stop INT,direction TEXT,source TEXT,version TEXT); '
                                     'CREATE TABLE gene_amino_acid_sequences(gene_callers_id INT,sequence TEXT); '
                                     'CREATE TABLE gene_functions(gene_callers_id INT,source TEXT,accession TEXT,function TEXT,e_value REAL);')
            connection.executemany('INSERT INTO self VALUES (?,?)', [('version', '20'), ('db_type', 'contigs'), ('gene_function_sources', 'COG14_FUNCTION,Pfam')])
            connection.executemany('INSERT INTO contig_sequences VALUES (?,?)', self.sequences.items())
            connection.executemany('INSERT INTO genes_in_contigs VALUES (?,?,?,?,?,?,?)',
                                   [(int(key), row['contig'], int(row['start']), int(row['stop']), row['direction'], row['source'], row['version']) for key, row in self.genes.items()])
            connection.executemany('INSERT INTO gene_amino_acid_sequences VALUES (?,?)', [(int(key), row['aa_sequence']) for key, row in self.genes.items()])
            connection.execute('INSERT INTO gene_functions VALUES (?,?,?,?,?)', (0, 'Pfam', 'PF00001.2', 'original annotation', 1e-20))
        self.annotations.write_text('gene_callers_id\tsource\taccession\tfunction\te_value\n0\tPfam\tPF00001.2\toriginal annotation\t1e-20\n')
        px.validate_anvio(database, self.genes, self.sequences, self.annotations)
        self.annotations.write_text('gene_callers_id\tsource\taccession\tfunction\te_value\n0\tCOG14_FUNCTION\tCOG0001\tforeign annotation\t1e-10\n')
        self.assertEqual(len(px.check_annotations(self.annotations, self.genes)), 1)
        with self.assertRaisesRegex(ValueError, 'this sample database'):
            px.validate_anvio(database, self.genes, self.sequences, self.annotations)

    def test_annotation_identity_coordinates_and_versions(self):
        self.assertEqual(px.check_annotations(self.annotations, self.genes)[0]['accession'], 'PF00001.2')
        for text in ['0\tPfam\tPF00001\t1e-20', '0\tCOG20_FUNCTION\tCOG0001\t1e-20',
                     '999\tPfam\tPF00001.2\t1e-20', '0\tPfam\tPF00001.2\tNaN']:
            self.annotations.write_text('gene_callers_id\tsource\taccession\te_value\n' + text + '\n')
            with self.subTest(text=text), self.assertRaises(ValueError):
                px.check_annotations(self.annotations, self.genes)
        self.denovo.write_text('gene_callers_id\tcontig\tstart\tstop\tdirection\te_value\taccession\n0\t' + self.keys[1] + '\t0\t9\tf\t0\tmmseqs_90_123\n')
        with self.assertRaisesRegex(ValueError, 'another gene'):
            px.check_annotations(self.denovo, self.genes, de_novo=True)

    def test_missing_duplicate_foreign_and_nonfinite_scores_fail(self):
        for rows in ['', self.keys[0] + '\t0.9\n' + self.keys[0] + '\t0.9\n',
                     'other\t0.9\n', self.keys[0] + '\tNaN\n', self.keys[0] + '\t1.1\n']:
            self.scores.write_text('contig\tscore\n' + rows)
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.finish()

    def test_all_unannotated_is_unassessed_without_fabricated_scores(self):
        self.annotations.write_text('gene_callers_id\tsource\taccession\te_value\n')
        self.scores.write_text('contig\tscore\n')
        result = self.finish()
        self.assertEqual(result['scored_contigs'], 0)
        self.assertEqual((self.base / 'output.tsv').read_text(), 'contig\tscore\n')


class PlasXExecution(unittest.TestCase):
    def test_partial_output_and_error_inside_worker_are_not_success(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)

            def native(command, log):
                return subprocess.run(command, stdout=subprocess.DEVNULL).returncode

            run = anvio_checked.checked_command(native, root / 'worker.jsonl')

            def worker():
                try:
                    run(['/bin/bash', '-c', 'echo partial > "$1"; exit 7', 'bash', str(root / 'partial')], str(root / 'log'))
                except RuntimeError:
                    raise SystemExit(19)

            process = multiprocessing.get_context('fork').Process(target=worker)
            process.start()
            process.join(10)
            self.assertFalse(process.is_alive())
            self.assertEqual(process.exitcode, 19)
            self.assertTrue((root / 'partial').is_file())
            self.assertIn('"exit_code": 7', (root / 'worker.jsonl').read_text())

    def test_failed_native_pipeline_is_not_hidden_by_tee(self):
        with tempfile.TemporaryDirectory() as folder:
            pipeline = 'exit 7 | tee ' + str(Path(folder) / 'log')
            self.assertEqual(subprocess.run(pipeline, shell=True).returncode, 0)
            audit = checked.CheckedProcesses()
            child = audit.popen(pipeline, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            child.communicate()
            self.assertEqual(child.returncode, 7)
            self.assertEqual(audit.records()[0]['exit_code'], 7)


class PlasXReferences(unittest.TestCase):
    def test_latest_pfam_cannot_replace_trained_version(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'Pfam.version').write_text('Pfam release : 35.0\n')
            with self.assertRaisesRegex(ValueError, 'Pfam32.0'):
                px.check_resources(pfam_db=root)

    def test_all_ten_profile_groups_are_required(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for identity in [90, 80, 70, 60, 50, 40, 30, 25, 20, 5]:
                for suffix in ['', '.dbtype', '.index', '_h', '_h.index']:
                    (root / ('clu' + str(identity) + '.profile' + suffix)).write_text('REFERENCE_STRUCTURE_CONTROL_ONLY\n')
            for name in ['rep_lengths.pkl.blp', 'rep_min_align_identity.pkl.blp']:
                (root / name).write_text('REFERENCE_STRUCTURE_CONTROL_ONLY\n')
            self.assertEqual(len(px.check_resources(profiles=root)['de_novo_identities']), 10)
            (root / 'clu5.profile.index').unlink()
            with self.assertRaisesRegex(ValueError, 'clu5.profile.index'):
                px.check_resources(profiles=root)

    def test_partial_or_nonfinite_model_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            model = Path(folder) / 'model.tsv'
            for rows in ['INTERCEPT\t0\nCOG0001\t1\nPF00001.2\t1\n',
                         'INTERCEPT\t0\nCOG0001\t1\nPF00001.2\t1\nmmseqs_90_1\tNaN\n']:
                model.write_text('accession\tPlasX_coefficient\n' + rows)
                with self.subTest(rows=rows), self.assertRaises(ValueError):
                    px.check_resources(model=model)


if __name__ == '__main__':
    unittest.main()
