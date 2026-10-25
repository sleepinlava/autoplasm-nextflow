"""Duplicate evidence must fail before consensus tables or FASTA are written."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ConsensusIntegrityTests(unittest.TestCase):
    def check_duplicate(self, kind, reverse=False):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);assembly=base/'assembly.fa';summary=base/'genomad.tsv'
            assembly.write_text('>p1 original\nACGT\n>p2\nACGTTGCA\n')
            summary.write_text('seq_name\tplasmid_score\np1\t0.9\n')
            extras=[];source=assembly
            if kind=='assembly':assembly.write_text('>p1 original\nACGT\n>p1 alternate\nACGTTGCA\n')
            elif kind=='genomad':
                source=summary;summary.write_text('seq_name\tplasmid_score\np1\t0.9\np1\t0.2\n')
            elif kind in ['table','identical']:
                source=base/'S.platon.tsv';rows=['p1\tplasmid',' p1 \tchromosome']
                if kind=='identical':rows=['p1\tplasmid','p1\tplasmid']
                if reverse:rows.reverse()
                source.write_text('contig_id\tclassification\n'+'\n'.join(rows)+'\n');extras=[source]
            elif kind=='tool_sources':
                source=base/'second.platon.tsv';first=base/'first.platon.tsv'
                first.write_text('contig_id\n'+'p1\n');source.write_text('contig_id\np2\n');extras=[first,source]
            outputs=[base/'out.fa',base/'predictions.tsv',base/'consensus.tsv']
            args=['Rscript',str(ROOT/'bin/plasmid_consensus.R'),'--assembly',str(assembly),'--genomad-summary',str(summary)]
            for extra in extras:args+=['--extra',str(extra)]
            args+=['--out-fasta',str(outputs[0]),'--out-predictions',str(outputs[1]),'--out-consensus',str(outputs[2])]
            r=subprocess.run(args,capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0,f'{kind}: duplicate was accepted')
            self.assertIn('Duplicate',r.stderr);self.assertIn(str(source),r.stderr)
            if kind!='tool_sources':
                self.assertIn('p1',r.stderr)
                self.assertIn('record 2',r.stderr)
                self.assertIn('first seen at record 1',r.stderr)
            else:
                self.assertIn(str(first),r.stderr)
            for output in outputs:self.assertFalse(output.exists(),str(output))

    def test_duplicate_normalized_assembly_ids(self):self.check_duplicate('assembly')
    def test_duplicate_genomad_records(self):self.check_duplicate('genomad')
    def test_conflicting_rows_rejected_in_either_order(self):
        for reverse in [False,True]:
            with self.subTest(reverse=reverse):self.check_duplicate('table',reverse)
    def test_multiple_files_for_same_tool_rejected(self):self.check_duplicate('tool_sources')
    def test_identical_duplicate_rows_are_also_rejected(self):self.check_duplicate('identical')


if __name__=='__main__':unittest.main()
