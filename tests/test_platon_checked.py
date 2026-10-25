import csv
from collections import Counter
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('platon_checked', ROOT/'bin/platon_checked.py')
checked = importlib.util.module_from_spec(spec); spec.loader.exec_module(checked)


class PlatonChecked(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_actual_child_nonzero_and_check_output_error_are_recorded(self):
        audit = checked.ChildAudit()
        result = audit.run([sys.executable, '-c', 'import sys;sys.exit(7)'], capture_output=True)
        self.assertEqual(result.returncode, 7)
        self.assertEqual(audit.failures()[0][0]['exit_code'], 7)
        with self.assertRaises(subprocess.CalledProcessError):
            audit.run([sys.executable, '-c', 'import sys;sys.exit(8)'], check=True, capture_output=True)
        self.assertEqual(len(audit.failures()[0]), 2)

    def test_unobserved_real_future_exception_is_not_discarded(self):
        audit = checked.ChildAudit()
        def fail(): raise ValueError('ACTUAL_THREAD_CONTROL')
        with checked.executor(audit)(1) as pool: pool.submit(fail)
        self.assertEqual(audit.failures()[1], ['ValueError: ACTUAL_THREAD_CONTROL'])

    def test_only_known_empty_postfilter_HMM_query_is_exempt(self):
        query = self.root/'proteins-filtered.faa'; query.write_text('')
        self.assertTrue(checked.ChildAudit.empty_annotation_query(['hmmsearch', 'model', str(query)]))
        self.assertFalse(checked.ChildAudit.empty_annotation_query(['diamond', 'model', str(query)]))
        other = self.root/'proteins.faa'; other.write_text('')
        self.assertFalse(checked.ChildAudit.empty_annotation_query(['hmmsearch', 'model', str(other)]))
        query.write_text('>protein\nMSEQ\n')
        self.assertFalse(checked.ChildAudit.empty_annotation_query(['hmmsearch', 'model', str(query)]))

    def test_logging_compatibility_changes_only_four_log_statements_and_no_package_bytes(self):
        import platon.platon as program
        original = Path(program.pf.__file__).read_bytes()
        record = checked.repair_no_hit_logging(program)
        # SequenceMatcher may include an unchanged repeated return at the tail
        # of a hunk. Cancel identical removed/added lines before comparing edits.
        removed = Counter(line[1:] for line in record['diff'].splitlines() if line.startswith('-') and not line.startswith('---'))
        added = Counter(line[1:] for line in record['diff'].splitlines() if line.startswith('+') and not line.startswith('+++'))
        old, new = removed-added, added-removed
        self.assertEqual(sum(old.values()), 4); self.assertEqual(sum(new.values()), 4)
        self.assertTrue(all(line.strip().startswith('log.info(') for line in [*old, *new]))
        self.assertEqual(Path(program.pf.__file__).read_bytes(), original)
        self.assertEqual(checked.sha(Path(program.pf.__file__)), checked.SOURCE_SHA256['functions.py'])

    def test_duplicate_empty_record_and_path_IDs_are_rejected(self):
        path = self.root/'bad.fa'
        for content in ['>dup\nACGT\n>dup\nTGCA\n', '>empty\n', '>../outside\nACGT\n']:
            path.write_text(content)
            with self.assertRaises(ValueError): checked.fasta(path)

    def products(self, prefix, positive):
        import platon.constants as pc
        dna = 'ACGT'*300
        detail = {'sequence':dna,'length':1200,'protein_score':29.04,'is_circular':False,
                  'orfs':{'gene':{}},'inc_types':[],'replication_hits':[],'mobilization_hits':[],
                  'orit_hits':[],'conjugation_hits':[],'amr_hits':[],'rrnas':[],'plasmid_hits':[]}
        prefix.with_suffix('.tsv').write_text(pc.HEADER+'\n'+('p\t1200\tNA\t1\t29.0\tno\t0\t0\t0\t0\t0\t0\t0\t0\n' if positive else ''))
        Path(str(prefix)+'.plasmid.fasta').write_text('>p\n'+dna+'\n' if positive else '')
        Path(str(prefix)+'.chromosome.fasta').write_text('' if positive else '>p\n'+dna+'\n')
        prefix.with_suffix('.json').write_text(json.dumps({'p':detail} if positive else {}))
        return {'p':dna}, pc.HEADER

    def test_outputs_require_source_DNA_IDs_lengths_and_annotation_counts(self):
        prefix=self.root/'positive'; records,header=self.products(prefix,True)
        state=checked.validate_outputs(str(prefix),records,{'p'},header)
        self.assertEqual(state['state'],'plasmids_found');self.assertEqual(state['plasmid_ids'],['p'])
        file=Path(str(prefix)+'.plasmid.fasta');file.write_text('>p\n'+'TGCA'*300+'\n')
        with self.assertRaisesRegex(ValueError,'DNA'):checked.validate_outputs(str(prefix),records,{'p'},header)
        self.products(prefix,True)
        file=prefix.with_suffix('.tsv');file.write_text(file.read_text().replace('\t1200\t','\t1199\t'))
        with self.assertRaisesRegex(ValueError,'length'):checked.validate_outputs(str(prefix),records,{'p'},header)

    def test_assessed_zero_is_distinct_from_unassessed_length_filter(self):
        prefix=self.root/'zero';records,header=self.products(prefix,False)
        state=checked.validate_outputs(str(prefix),records,{'p'},header)
        self.assertEqual(state['state'],'no_plasmids');self.assertFalse(state['compatibility_empty_products'])
        prefix=self.root/'short'
        state=checked.validate_outputs(str(prefix),{'short':'ACGT'*200},set(),header)
        self.assertEqual(state['state'],'not_assessed_length_filter');self.assertEqual(state['not_assessed_ids'],['short'])
        self.assertTrue(state['compatibility_empty_products'])
        self.assertFalse(Path(str(prefix)+'.chromosome.fasta').exists())

    def test_partial_outputs_for_unassessed_state_are_not_silently_repaired(self):
        import platon.constants as pc
        prefix=self.root/'partial';prefix.with_suffix('.tsv').write_text('BAD\n')
        with self.assertRaisesRegex(ValueError,'Unexpected products'):
            checked.validate_outputs(str(prefix),{'short':'ACGT'},set(),pc.HEADER)


if __name__=='__main__':unittest.main()
