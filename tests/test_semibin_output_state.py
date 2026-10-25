import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('semibin_state',ROOT/'bin/semibin_output_state.py')
adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)


class SemiBinState(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.bins=self.root/'output_bins';self.bins.mkdir()
        self.summary=self.root/'recluster_bins_info.tsv'
        self.header='filename\tnbps\tnr_contigs\tN50\tL50\n'
        self.summary.write_text(self.header)

    def test_valid_zero_bins_is_explicit_and_does_not_create_fasta(self):
        # The pre-filter label table may have positives; only final output
        # FASTAs and the post-reclustering table determine the retained state.
        (self.root/'contig_bins.tsv').write_text('contig\tbin\nfiltered\t0\n')
        value=adapter.record_state(self.root)
        self.assertEqual((value['state'],value['bin_count'],value['bins']),('no_bins',0,[]))
        self.assertEqual(list(self.bins.iterdir()),[])
        self.assertEqual(json.loads((self.root/'binning_status.json').read_text()),value)

    def test_positive_final_bin_uses_postfilter_summary(self):
        fasta=self.bins/'SemiBin_3.fa.gz';fasta.write_bytes(gzip.compress(b'>a\nACGTTGCA\n'))
        self.summary.write_text(self.header+str(fasta)+'\t8\t1\t8\t1\n')
        value=adapter.record_state(self.root)
        self.assertEqual(value['state'],'bins_ready');self.assertEqual(value['bin_count'],1)
        self.assertEqual(value['bins'],[{'filename':'SemiBin_3.fa.gz','nbps':8,'nr_contigs':1,'N50':8,'L50':1}])

    def test_missing_corrupt_or_stale_output_cannot_be_reported_as_empty(self):
        fasta=self.bins/'SemiBin_0.fa.gz'
        for payload in [b'',gzip.compress(b'>a\nACGT\n')]:
            fasta.write_bytes(payload)
            with self.assertRaises(ValueError):adapter.record_state(self.root)
            self.assertFalse((self.root/'binning_status.json').exists())
        fasta.unlink();self.summary.write_text(self.header+str(fasta)+'\t4\t1\t4\t1\n')
        with self.assertRaisesRegex(ValueError,'sets differ'):adapter.record_state(self.root)
        self.assertFalse((self.root/'binning_status.json').exists())

    def test_wrong_header_compression_and_duplicate_summary_fail(self):
        self.summary.write_text('filename\tcount\n')
        with self.assertRaisesRegex(ValueError,'header'):adapter.record_state(self.root)
        self.summary.write_text(self.header);wrong=self.bins/'bin.fa';wrong.write_text('>a\nACGT\n')
        with self.assertRaisesRegex(ValueError,'compression'):adapter.record_state(self.root)
        wrong.unlink();fasta=self.bins/'bin.fa.gz';fasta.write_bytes(gzip.compress(b'>a\nACGT\n'))
        row=str(fasta)+'\t4\t1\t4\t1\n';self.summary.write_text(self.header+row+row)
        with self.assertRaisesRegex(ValueError,'Duplicate'):adapter.record_state(self.root)


if __name__=='__main__':unittest.main()
