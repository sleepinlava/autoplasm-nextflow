"""Boundary observers around actual native modules, never biological inference."""
import importlib
from pathlib import Path
import sys
import tempfile
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'bin'))
import mobsuite_preflight as guard
from ete3 import NCBITaxa
import mob_suite.mob_init as initializer
import mob_suite.utils as utils


class ExecutionBoundary(unittest.TestCase):
    def test_typer_uses_real_native_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            args,paths=guard.native_resource_paths(['--infile','NO_SEQUENCE_OPENED.fa','--out_file','NO_REPORT.txt','-d',directory],'mob_typer')
            self.assertEqual(paths['ETE3DBTAXAFILE'],str(Path(directory)/'taxa.sqlite'))
            self.assertNotIn('plasmid_ref_db',paths)
            self.assertEqual(len(paths),10)  # includes NCBI metadata alias

    def test_unprepared_execute_refuses_both_before_native_main(self):
        for tool,output in [('mob_recon','--outdir'),('mob_typer','--out_file')]:
            module=importlib.import_module('mob_suite.'+tool)
            with patch.object(module,'main') as native,patch.object(utils,'Popen',side_effect=AssertionError('no child')) as child:
                with patch.object(sys,'argv',['guard','--tool',tool,'--execute','--','--infile','NO_INPUT.fa',output,'NO_OUTPUT']):
                    with self.assertRaises(SystemExit) as status:guard.main()
                self.assertEqual(status.exception.code,2);native.assert_not_called();child.assert_not_called()

    def test_status_disappearance_refused_at_native_boundary(self):
        for tool in ['mob_recon','mob_typer']:
            module=importlib.import_module('mob_suite.'+tool)
            with tempfile.TemporaryDirectory() as directory:
                def observer():module.verify_init(None,directory)
                old=module.verify_init
                with patch.object(module,'main',side_effect=observer),patch.object(utils,'Popen',side_effect=AssertionError('no child')):
                    with self.assertRaisesRegex(guard.PreparationRequired,'became unprepared'):guard.guarded_main(tool,[])
                self.assertIs(module.verify_init,old)

    def test_ete3_update_is_denied_and_restored(self):
        for tool in ['mob_recon','mob_typer']:
            module=importlib.import_module('mob_suite.'+tool);old=NCBITaxa.update_taxonomy_database
            def observer():NCBITaxa.update_taxonomy_database(object.__new__(NCBITaxa))
            with patch.object(module,'main',side_effect=observer):
                with self.assertRaisesRegex(guard.PreparationRequired,'upgrade is prohibited'):guard.guarded_main(tool,[])
            self.assertIs(NCBITaxa.update_taxonomy_database,old)

    def test_direct_initializer_is_denied(self):
        for tool in ['mob_recon','mob_typer']:
            module=importlib.import_module('mob_suite.'+tool);old=initializer.main
            with patch.object(module,'main',side_effect=lambda:initializer.main()):
                with self.assertRaisesRegex(guard.PreparationRequired,'initialization or upgrade'):guard.guarded_main(tool,[])
            self.assertIs(initializer.main,old)

    def test_prepared_taxonomy_metadata_is_opened_readonly(self):
        from ete3.ncbi_taxonomy import ncbiquery
        for tool in ['mob_recon','mob_typer']:
            module=importlib.import_module('mob_suite.'+tool)
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'CONTROL_METADATA.sqlite'
                with sqlite3.connect(path) as db:
                    db.executescript("CREATE TABLE stats(version INTEGER);INSERT INTO stats VALUES(2);CREATE TABLE species(taxid INTEGER,parent INTEGER,spname TEXT,common TEXT,rank TEXT,track TEXT);INSERT INTO species VALUES(1,1,'CONTROL_METADATA','','no rank','1');CREATE TABLE synonym(taxid INTEGER,spname TEXT);CREATE TABLE merged(taxid_old INTEGER,taxid_new INTEGER);")
                old_connect=NCBITaxa._connect;old_current=ncbiquery.is_taxadb_up_to_date;before=path.read_bytes()
                def observer():
                    ncbi=NCBITaxa(dbfile=str(path))
                    self.assertEqual(ncbi.get_lineage(1),[1])
                    with self.assertRaisesRegex(sqlite3.OperationalError,'readonly'):ncbi.db.execute('INSERT INTO stats VALUES(99)')
                    ncbi.db.close()
                with patch.object(module,'main',side_effect=observer):guard.guarded_main(tool,[])
                self.assertEqual(path.read_bytes(),before)
                self.assertIs(NCBITaxa._connect,old_connect);self.assertIs(ncbiquery.is_taxadb_up_to_date,old_current)

    def test_execution_does_not_disable_original_optional_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'CONTROL_METADATA_ONLY';path.write_text('CONTROL')
            parsed=SimpleNamespace(filter_db='ORIGINAL_FILTER_ARGUMENT',genome_filter_db_prefix=None)
            with patch.object(guard,'native_resource_paths',return_value=(parsed,{'ETE3DBTAXAFILE':str(path)})),patch.object(guard,'taxonomy_schema',return_value=2):
                with self.assertRaisesRegex(guard.PreparationRequired,'has not been implemented'):guard.check([])
                result=guard.check([],allow_optional=True)
                self.assertTrue(result['optional_filter_validation_deferred'])

    def test_prepared_boundary_preserves_argv_return_and_python_state(self):
        for tool in ['mob_recon','mob_typer']:
            module=importlib.import_module('mob_suite.'+tool)
            with tempfile.TemporaryDirectory() as directory:
                (Path(directory)/'status.txt').write_text('CONTROL_METADATA_ONLY\n')
                expected=['--infile','data with spaces.fa','--sample_id','A__1.v1'];saved=sys.argv
                def observer():
                    self.assertEqual(sys.argv,[tool]+expected)
                    module.verify_init(None,directory)
                    return 17
                with patch.object(module,'main',side_effect=observer),patch.object(utils,'Popen',side_effect=AssertionError('no child')):
                    self.assertEqual(guard.guarded_main(tool,expected),17)
                self.assertIs(sys.argv,saved)


if __name__=='__main__':unittest.main()
