import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gtdb_inputs', ROOT/'bin/normalize_gtdb_bins.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class GenomeInputs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root/'bins';self.inputs.mkdir()
        self.output = self.root/'normalized'
        self.manifest = self.root/'genomes.json'
        # Deliberately retain CRLF, lowercase, ambiguity, multiple records and
        # absent final newline. Normalization must preserve the FASTA bytes.
        self.dna = b'>contigA description\r\nacgtNRY\r\n>contigB\r\nTTGCA'

    def run_adapter(self):
        return adapter.normalize(self.inputs,self.output,self.manifest)

    def assert_clean_failure(self, diagnostic):
        with self.assertRaisesRegex(ValueError,diagnostic):self.run_adapter()
        self.assertFalse(self.output.exists())
        self.assertFalse(self.manifest.exists())

    def test_mixed_suffixes_preserve_genome_stems_and_exact_fasta_bytes(self):
        expected={}
        for name,compressed in [('A.1.fa',False),('B.2.fna.gz',True),('C.fasta',False),('D.FA.GZ',True)]:
            stem=name.split('.')[0] if name.startswith(('C.','D.')) else '.'.join(name.split('.')[:2])
            payload=self.dna.replace(b'contigB',stem.encode())
            (self.inputs/name).write_bytes(gzip.compress(payload,mtime=0) if compressed else payload)
            expected[stem+'.fna']=payload
        before={p.name:p.read_bytes() for p in self.inputs.iterdir()}
        result=self.run_adapter()
        self.assertEqual({p.name:p.read_bytes() for p in self.output.iterdir()},expected)
        self.assertEqual({p.name:p.read_bytes() for p in self.inputs.iterdir()},before)
        self.assertEqual(result['genomes'],4)
        self.assertEqual({r['genome_id'] for r in result['files']},{'A.1','B.2','C','D'})
        self.assertEqual(json.loads(self.manifest.read_text()),result)

    def test_duplicate_stems_refuse_overwrite_before_output(self):
        (self.inputs/'same.fa').write_bytes(self.dna)
        (self.inputs/'same.FNA.GZ').write_bytes(gzip.compress(b'>different\nTTAA'))
        self.assert_clean_failure('Duplicate GTDB-Tk genome ID')

    def test_invalid_native_genome_identifiers_are_not_silently_renamed(self):
        for name in ['a b.fa','a,b.fna','a;b.fa','a=b.fasta','a(b).fa','a[b].fa','a\tb.fa','.fa']:
            with self.subTest(name=name):
                file=self.inputs/name;file.write_bytes(self.dna)
                self.assert_clean_failure('Invalid GTDB-Tk genome ID')
                file.unlink()

    def test_bad_or_truncated_gzip_never_leaves_partial_bin_set(self):
        (self.inputs/'A.fa').write_bytes(self.dna)
        bad=self.inputs/'Z.fa.gz'
        for data in [b'not gzip',gzip.compress(self.dna)[:-6]]:
            bad.write_bytes(data)
            with self.assertRaises((ValueError,OSError,EOFError)):self.run_adapter()
            self.assertFalse(self.output.exists());self.assertFalse(self.manifest.exists())

    def test_empty_directory_and_non_fasta_are_errors_not_absent_genomes(self):
        self.assert_clean_failure('directory is empty')
        file=self.inputs/'empty.fa'
        for data in [b'',b'\n\r\n',b'ACGTACGT']:
            file.write_bytes(data);self.assert_clean_failure('Empty or non-FASTA')

    def test_unexpected_files_or_directories_cannot_be_silently_skipped(self):
        (self.inputs/'good.fa').write_bytes(self.dna)
        unexpected=self.inputs/'not_genomes.tsv';unexpected.write_text('ID\tdata\n')
        self.assert_clean_failure('Unsupported GTDB-Tk bin FASTA suffix')
        unexpected.unlink();(self.inputs/'nested').mkdir()
        self.assert_clean_failure('not a file')

    def test_exact_retry_is_safe_but_stale_or_changed_files_fail(self):
        (self.inputs/'A.fa').write_bytes(self.dna)
        first=self.run_adapter();self.assertEqual(self.run_adapter(),first)
        self.manifest.unlink();(self.output/'A.fna').write_bytes(b'>stale\nATGC')
        with self.assertRaisesRegex(ValueError,'differs'):self.run_adapter()
        self.assertFalse(self.manifest.exists())
        (self.output/'A.fna').write_bytes(self.dna);(self.output/'stale.fna').write_bytes(self.dna)
        with self.assertRaisesRegex(ValueError,'unexpected contents'):self.run_adapter()

    def test_outputs_cannot_overwrite_or_pollute_input_directory(self):
        original=self.inputs/'A.fa';original.write_bytes(self.dna)
        for destination,manifest in [(self.inputs,self.manifest),(self.inputs/'subdir',self.manifest),
                                     (self.output,original),(self.output,self.output/'manifest.json')]:
            with self.assertRaises(ValueError):adapter.normalize(self.inputs,destination,manifest)
            self.assertEqual(original.read_bytes(),self.dna)
            self.assertFalse(self.output.exists())

    def test_gzip_magic_without_gz_suffix_is_decoded_without_changing_identity(self):
        (self.inputs/'A.fasta').write_bytes(gzip.compress(self.dna,mtime=0))
        result=self.run_adapter()
        self.assertEqual((self.output/'A.fna').read_bytes(),self.dna)
        self.assertEqual(result['files'][0]['genome_id'],'A')
        self.assertTrue(result['files'][0]['gzip_decoded'])


if __name__=='__main__':unittest.main()
