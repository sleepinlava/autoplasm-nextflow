"""Actual installed3.1.9 parser plus synthetic file/schema readiness controls.

No MOB science/init/download. Positive structural control contains deliberately
non-biological placeholder resources and cannot establish scientific DB validity.
"""
from pathlib import Path
import hashlib
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'bin'))
import mobsuite_preflight as preflight
import mob_suite.mob_recon as recon
import mob_suite.utils as utils
import mob_suite.constants as constants


class PreparationChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.database=self.root/'database';self.database.mkdir()
        self.argv=['-i',str(self.root/'NO_SEQUENCE_CREATED.fa'),'-o',str(self.root/'NO_OUTPUT_CREATED')]
        # Any accidental native DB initializer/ETE object/child process fails.
        for target in ['mob_suite.utils.Popen','mob_suite.mob_recon.verify_init','mob_suite.utils.NCBITaxa']:
            p=patch(target,side_effect=AssertionError('Initialization/science must not run'))
            p.start();self.addCleanup(p.stop)

    def custom(self,*extra):return self.argv+['-d',str(self.database),*extra]

    def placeholders(self):
        _,paths=preflight.native_resource_paths(self.custom())
        for value in set(paths.values()):Path(value).write_bytes(b'EXPLICIT_NONBIOLOGICAL_PLACEHOLDER\n')
        return paths

    def schema(self,version=2,complete=True):
        p=self.database/'taxa.sqlite'
        if p.exists():p.unlink()
        with sqlite3.connect(p) as db:
            db.execute('CREATE TABLE stats(version INTEGER)');db.execute('INSERT INTO stats VALUES(?)',(version,))
            if complete:
                db.execute('CREATE TABLE species(taxid INTEGER,parent INTEGER,spname TEXT,common TEXT,rank TEXT,track TEXT)')
                db.execute("INSERT INTO species VALUES(1,1,'CONTROL_METADATA_ONLY','','no rank','1')")
                db.execute('CREATE TABLE synonym(taxid INTEGER,spname TEXT)')
                db.execute('CREATE TABLE merged(taxid_old INTEGER,taxid_new INTEGER)')
        return p

    def test_actual_default_missing_status_refused_without_init(self):
        original=Path(constants.default_database_dir)
        before=sorted(x.name for x in original.iterdir())
        self.assertNotIn('status.txt',before)
        with self.assertRaisesRegex(preflight.PreparationRequired,'automatic initialization is prohibited'):
            preflight.check(self.argv)
        self.assertEqual(before,sorted(x.name for x in original.iterdir()))
        self.assertFalse((self.root/'NO_OUTPUT_CREATED').exists())

    def test_native_custom_directory_ignores_individual_override(self):
        args,paths=preflight.native_resource_paths(self.custom('--plasmid_db','/OVERRIDE_NOT_OPENED.fa'))
        self.assertEqual(args.plasmid_db,'/OVERRIDE_NOT_OPENED.fa')
        self.assertEqual(paths['plasmid_ref_db'],str(self.database/'ncbi_plasmid_full_seqs.fas'))

    def test_missing_and_empty_required_resources_refused(self):
        with self.assertRaisesRegex(preflight.PreparationRequired,'missing/empty'):
            preflight.check(self.custom())
        self.placeholders();self.schema();(self.database/'rep.dna.fas').write_bytes(b'')
        with self.assertRaisesRegex(preflight.PreparationRequired,'replicon_ref'):
            preflight.check(self.custom())

    def test_invalid_sqlite_refused(self):
        self.placeholders()
        with self.assertRaisesRegex(preflight.PreparationRequired,'Invalid prepared ETE3'):
            preflight.check(self.custom())

    def test_outdated_taxonomy_refused_without_upgrade(self):
        self.placeholders();p=self.schema(version=1);before=p.read_bytes();st=p.stat()
        with self.assertRaisesRegex(preflight.PreparationRequired,'automatic upgrade is prohibited'):
            preflight.check(self.custom())
        self.assertEqual(p.read_bytes(),before);self.assertEqual(p.stat().st_mtime_ns,st.st_mtime_ns)
        self.assertFalse(list(self.database.glob('*.sqlite-*')))

    def test_incomplete_taxonomy_tables_refused(self):
        self.placeholders();self.schema(complete=False)
        with self.assertRaisesRegex(preflight.PreparationRequired,'Incomplete ETE3'):
            preflight.check(self.custom())

    def test_structural_control_readonly_not_scientific_certificate(self):
        self.placeholders();self.schema();before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.database.iterdir()}
        result=preflight.check(self.custom())
        self.assertTrue(result['preparation_presence_checks'])
        self.assertIn('No native science',result['scope'])
        self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.database.iterdir()})

    def test_optional_filters_and_changed_sources_remain_refused(self):
        with self.assertRaisesRegex(preflight.PreparationRequired,'has not been implemented'):
            preflight.check(self.custom('--filter_db','/UNOPENED_FILTER'))
        with patch.dict(preflight.EXPECTED_SOURCE,{'mob_recon.py':'0'*64}):
            with self.assertRaisesRegex(preflight.PreparationRequired,'source differs'):
                preflight.check(self.custom())


if __name__=='__main__':unittest.main()
