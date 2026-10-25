import csv
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('hotspot_lineage',ROOT/'bin/convert_hotspot_lineage.py')
adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)


class HotspotLineage(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.input=self.root/'lineage.tsv';self.output=self.root/'links.tsv';self.manifest=self.root/'conversion.json'

    def write(self,rows,ending='\r\n',header=None):
        with self.input.open('w',newline='') as stream:
            writer=csv.writer(stream,delimiter='\t',lineterminator=ending);writer.writerow(adapter.INPUT_HEADER if header is None else header);writer.writerows(rows)

    def convert(self,fasta=None):return adapter.convert(self.input,'sample.1',self.output,self.manifest,fasta)

    def rows(self):
        with self.output.open(newline='') as stream:return list(csv.DictReader(stream,delimiter='\t'))

    def test_crlf_and_lf_missing_species_fall_back_to_genus_exactly(self):
        for ending in ['\r\n','\n']:
            self.write([['p1','P','C','O','F','KnownGenus','-']],ending)
            value=self.convert();row=self.rows()[0]
            self.assertEqual(row,{'plasmid_id':'p1','host_id':'KnownGenus','sample_id':'sample.1','evidence_type':'hotspot','score':'','supporting_data':'method=hotspot;lineage=P>C>O>F>KnownGenus'})
            self.assertEqual(value['host_links'],1);self.assertNotIn(b'\r',self.output.read_bytes())
            self.output.unlink();self.manifest.unlink()

    def test_each_deepest_rank_keeps_the_upstream_name_without_placeholders(self):
        expected={};rows=[]
        for depth in range(1,7):
            ranks=['Taxon'+str(i) for i in range(depth)]+['-']*(6-depth)
            rows.append(['p'+str(depth),*ranks]);expected['p'+str(depth)]=ranks[depth-1]
        self.write(rows);self.convert()
        self.assertEqual({r['plasmid_id']:r['host_id'] for r in self.rows()},expected)
        self.assertTrue(all(r['host_id'] not in ['','-'] for r in self.rows()))

    def test_all_missing_taxa_emit_no_host_and_record_the_unscored_id(self):
        self.write([['p1','-','','-','','-','-']]);value=self.convert()
        self.assertEqual(self.rows(),[]);self.assertEqual(value['no_taxon_in_lineage'],['p1']);self.assertEqual(value['lineage_rows'],1)

    def test_header_only_is_structural_empty_not_a_fabricated_prediction(self):
        fasta=self.root/'plasmids.fna';fasta.write_text('>missing\nACGT\n')
        self.write([]);value=self.convert(fasta)
        self.assertEqual(self.rows(),[]);self.assertEqual(value['source_ids_not_in_lineage'],['missing'])
        self.assertEqual(value['host_links'],0)

    def test_bad_header_or_rank_order_fails_before_outputs(self):
        for header in [['Contig',*adapter.RANKS[::-1]],['contig',*adapter.RANKS],adapter.INPUT_HEADER+['score']]:
            self.write([],header=header)
            with self.assertRaisesRegex(ValueError,'header'):self.convert()
            self.assertFalse(self.output.exists());self.assertFalse(self.manifest.exists())

    def test_malformed_rows_and_embedded_control_characters_fail_cleanly(self):
        for row in [['p1','P'],['p1','P','C','O','F','G','S','extra'],['p1','P','C','O','F','G','bad\rtaxon']]:
            self.write([row])
            with self.assertRaisesRegex(ValueError,'Malformed'):self.convert()
            self.assertFalse(self.output.exists());self.assertFalse(self.manifest.exists())

    def test_duplicate_or_foreign_ids_cannot_be_assigned_to_the_sample(self):
        fasta=self.root/'source.fna';fasta.write_text('>allowed\nACGT\n')
        for rows in [[['foreign','P','-','-','-','-','-']], [['allowed','P','-','-','-','-','-']]*2]:
            self.write(rows)
            with self.assertRaisesRegex(ValueError,'contig ID'):self.convert(fasta)
            self.assertFalse(self.output.exists());self.assertFalse(self.manifest.exists())

    def test_quoted_taxon_and_gzip_source_keep_ids_and_provenance(self):
        fasta=self.root/'source.fna.gz';fasta.write_bytes(gzip.compress(b'>p1 description\nACGT\n>unscored\nTGCA\n'))
        self.write([['p1','P','C','O','F','Genus "quoted"','Species with spaces']])
        value=self.convert(fasta)
        self.assertEqual(self.rows()[0]['host_id'],'Species with spaces')
        self.assertIn('Genus "quoted"',self.rows()[0]['supporting_data'])
        self.assertEqual(value['source_ids_not_in_lineage'],['unscored'])
        self.assertEqual(value['source_fasta_sha256'],hashlib.sha256(fasta.read_bytes()).hexdigest())
        self.assertEqual(json.loads(self.manifest.read_text()),value)

    def test_inputs_are_never_overwritten(self):
        self.write([['p1','P','-','-','-','-','-']]);before=self.input.read_bytes()
        with self.assertRaises(ValueError):adapter.convert(self.input,'S',self.input,self.manifest)
        self.assertEqual(self.input.read_bytes(),before);self.assertFalse(self.manifest.exists())


if __name__=='__main__':unittest.main()
