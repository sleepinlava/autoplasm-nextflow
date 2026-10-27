#!/usr/bin/env python3
"""Read-only preparation checks for fixed MOB-suite3.1.9, without running mob_init.

Checks presence and ETE3 schema readiness before optional guarded native main.
Only implicit MOB/ETE3 preparation is replaced; scientific code/argv stay native.
Complete DB content, cache identity, optional filters and nonviral provenance
remain outside this bounded candidate.
"""
import argparse
import ast
import hashlib
import json
import importlib
import os
from pathlib import Path
import sqlite3
import sys
from urllib.parse import quote

EXPECTED_SOURCE = {
    'mob_typer.py':'3fc7053ade859deea58fdeae4ab15d1ee21922e99c9cc2841d4c45d67a30e1b4',
    'mob_recon.py':'567143cd1477c1ed59fb833ddbd5db3167ba4ba55d48d4ae902fe377fbf64eb0',
    'utils.py':'ff0cdff8f7e2d9f3b5df93f87c65eba10d6b8a4c278165cd9a8c5c090e6640ed',
    'constants.py':'7aab451815d7e9032e530c425537dae632b6e3afcef6d9d1f87eaf528b1c2ea4',
    'mob_init.py':'9da81b0f28f492736bfd8b4500759a9f6e17d4c338445b249934ba0cb5ae736e',
    'version.py':'0e67f8204c7868d6c4e466de81757e632fa0229f0d785f5fa6fe0225cf8c598a',
    'config.json':'bb92211b7839fec435bdf3d16ba21e359741351dd74afa4be665b0e1b4e742d3',
}


class PreparationRequired(ValueError):
    pass


def native_resource_paths(native_args,tool='mob_recon'):
    if tool not in ['mob_recon','mob_typer']:raise PreparationRequired('Unsupported MOB entrypoint')
    recon=importlib.import_module('mob_suite.'+tool)
    from mob_suite.version import __version__
    from mob_suite.constants import default_database_dir
    package=Path(recon.__file__).parent
    if __version__!='3.1.9':raise PreparationRequired('Requires installed native MOB-suite3.1.9')
    for name,expected in EXPECTED_SOURCE.items():
        if hashlib.sha256((package/name).read_bytes()).hexdigest()!=expected:
            raise PreparationRequired('Fixed3.1.9 source differs: '+name)
    saved=sys.argv
    try:
        sys.argv=[tool]+list(native_args)
        args=recon.parse_args()
    finally:sys.argv=saved
    tree=ast.parse(Path(recon.__file__).read_text())
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    def assigns(n,name):return isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)
    statements=[]
    for node in main.body:
        if any(assigns(node,name) for name in ['database_dir','ETE3DBTAXAFILE','LIT_PLASMID_TAXONOMY_FILE','NCBI_PLASMID_TAXONOMY_FILE']):
            statements.append(node)
        elif isinstance(node,ast.If) and ast.unparse(node.test)=='database_dir == default_database_dir':
            statements.append(node)
    if len(statements)!=5:raise PreparationRequired('Unexpected fixed MOB DB selection boundary')
    def refuse_initialization(logger,directory):
        status=Path(directory)/'status.txt'
        if not status.is_file() or status.stat().st_size==0:
            raise PreparationRequired('MOB default DB is not prepared: missing/empty status.txt; automatic initialization is prohibited')
    namespace=dict(os=os,args=args,default_database_dir=default_database_dir,
                   verify_init=refuse_initialization,logger=None)
    # Only the original resource path-selection statements are executed.
    # Its verify_init call becomes a check that never starts an initializer.
    exec(compile(ast.Module(body=statements,type_ignores=[]),str(recon.__file__),'exec'),namespace)
    names=['plasmid_ref_db','mob_ref','mash_db','replicon_ref','plasmid_meta',
           'repetitive_mask_file','mpf_ref','plasmid_orit','ETE3DBTAXAFILE',
           'LIT_PLASMID_TAXONOMY_FILE','NCBI_PLASMID_TAXONOMY_FILE']
    return args,{name:namespace[name] for name in names if name in namespace}


def taxonomy_schema(path):
    from ete3.ncbi_taxonomy.ncbiquery import DB_VERSION
    # Never call NCBITaxa or is_taxadb_up_to_date: their default paths can
    # create a DB or trigger an upgrade/download. Require an existing ro file.
    connection=sqlite3.connect('file:'+quote(str(Path(path).resolve()),safe='/')+'?mode=ro',uri=True)
    try:
        version=connection.execute('SELECT version FROM stats').fetchone()
        if not version or version[0]!=DB_VERSION:
            raise PreparationRequired('ETE3 taxonomy schema needs preparation; automatic upgrade is prohibited')
        if connection.execute('PRAGMA quick_check').fetchone()!=('ok',):
            raise PreparationRequired('ETE3 taxonomy integrity check failed')
        required={'species':{'taxid','parent','spname','common','rank','track'},
                  'synonym':{'taxid','spname'},'merged':{'taxid_old','taxid_new'}}
        for table,columns in required.items():
            found={row[1] for row in connection.execute('PRAGMA table_info('+table+')')}
            if not columns<=found:raise PreparationRequired('Incomplete ETE3 taxonomy schema: '+table)
        if connection.execute('SELECT COUNT(*) FROM species').fetchone()[0]==0:
            raise PreparationRequired('Empty taxonomy species table')
        return DB_VERSION
    except sqlite3.DatabaseError as error:
        raise PreparationRequired('Invalid prepared ETE3 taxonomy: '+str(error)) from error
    finally:connection.close()


def check(native_args,tool='mob_recon',allow_optional=False):
    args,paths=native_resource_paths(native_args,tool)
    optional=bool(getattr(args,'filter_db',None) or getattr(args,'genome_filter_db_prefix',None))
    if optional and not allow_optional:
        raise PreparationRequired('Optional filter DB/prefix readiness has not been implemented; original native support remains pending validation')
    missing=[name for name,path in paths.items() if not Path(path).is_file() or Path(path).stat().st_size==0]
    if missing:raise PreparationRequired('Required prepared resources missing/empty: '+','.join(missing))
    version=taxonomy_schema(paths['ETE3DBTAXAFILE'])
    return dict(tool='MOB-suite',entrypoint=tool,version='3.1.9',preparation_presence_checks=True,
                taxonomy_schema_version=version,selected_paths=paths,optional_filter_validation_deferred=optional,
                scope='No native science invoked by this check; preparation presence/schema only, not full DB validity/cache identity/optional filter or nonviral provenance certification.')


def guarded_main(tool,native_args):
    """Run unchanged native main/argv, replacing only implicit preparers.

    Recheck status at the real verify_init call and deny all ETE3 update paths,
    so resources disappearing after preflight cannot start a download.
    """
    import mob_suite.utils as utils
    import mob_suite.mob_init as initializer
    from ete3 import NCBITaxa
    from ete3.ncbi_taxonomy import ncbiquery
    program=importlib.import_module('mob_suite.'+tool)
    def refuse_initialization(logger,directory):
        status=Path(directory)/'status.txt'
        if not status.is_file() or status.stat().st_size==0:
            raise PreparationRequired('MOB DB became unprepared; implicit initialization is prohibited')
    def deny_update(*args,**kwargs):
        raise PreparationRequired('Implicit MOB/ETE3 database initialization or upgrade is prohibited')
    def readonly_taxonomy_connect(self):
        try:
            self.db=sqlite3.connect('file:'+quote(str(Path(self.dbfile).resolve()),safe='/')+'?mode=ro',uri=True)
        except sqlite3.DatabaseError as error:
            raise PreparationRequired('Prepared taxonomy disappeared or is unreadable: '+str(error)) from error
    def readonly_taxonomy_current(dbfile=ncbiquery.DEFAULT_TAXADB):
        taxonomy_schema(dbfile)
        return True
    overrides=[(utils,'verify_init',refuse_initialization),
               (program,'verify_init',refuse_initialization),
               (initializer,'main',deny_update),
               (NCBITaxa,'update_taxonomy_database',deny_update),
               (NCBITaxa,'_connect',readonly_taxonomy_connect),
               (ncbiquery,'is_taxadb_up_to_date',readonly_taxonomy_current)]
    originals=[(obj,name,getattr(obj,name)) for obj,name,_ in overrides]
    saved=sys.argv
    try:
        for obj,name,value in overrides:setattr(obj,name,value)
        sys.argv=[tool]+list(native_args)
        return program.main()
    finally:
        sys.argv=saved
        for obj,name,value in reversed(originals):setattr(obj,name,value)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tool',choices=['mob_recon','mob_typer'],default='mob_recon')
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--output',type=Path)
    parser.add_argument('native_args',nargs=argparse.REMAINDER)
    args=parser.parse_args();native=args.native_args[1:] if args.native_args[:1]==['--'] else args.native_args
    try:
        result=check(native,args.tool,allow_optional=args.execute)
        text=json.dumps(result,sort_keys=True)+'\n'
        if args.output:args.output.write_text(text)
        elif not args.execute:print(text,end='')
        if args.execute:return guarded_main(args.tool,native)
    except (PreparationRequired,OSError) as error:parser.exit(2,str(error)+'\n')


if __name__=='__main__':sys.exit(main())
