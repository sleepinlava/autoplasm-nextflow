#!/usr/bin/env python3
"""Read-only preparation checks for fixed MOB-suite3.1.9, without running mob_init.

This standalone candidate checks presence and ETE3 schema readiness. It never
executes MOB science and does not certify complete DB content, cache identity,
optional filters or nonviral provenance. Production integration remains pending.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
from urllib.parse import quote

EXPECTED_SOURCE = {
    'mob_recon.py':'567143cd1477c1ed59fb833ddbd5db3167ba4ba55d48d4ae902fe377fbf64eb0',
    'utils.py':'ff0cdff8f7e2d9f3b5df93f87c65eba10d6b8a4c278165cd9a8c5c090e6640ed',
    'constants.py':'7aab451815d7e9032e530c425537dae632b6e3afcef6d9d1f87eaf528b1c2ea4',
    'mob_init.py':'9da81b0f28f492736bfd8b4500759a9f6e17d4c338445b249934ba0cb5ae736e',
    'version.py':'0e67f8204c7868d6c4e466de81757e632fa0229f0d785f5fa6fe0225cf8c598a',
    'config.json':'bb92211b7839fec435bdf3d16ba21e359741351dd74afa4be665b0e1b4e742d3',
}


class PreparationRequired(ValueError):
    pass


def native_resource_paths(native_args):
    import mob_suite.mob_recon as recon
    from mob_suite.version import __version__
    from mob_suite.constants import default_database_dir
    package=Path(recon.__file__).parent
    if __version__!='3.1.9':raise PreparationRequired('Requires installed native MOB-suite3.1.9')
    for name,expected in EXPECTED_SOURCE.items():
        if hashlib.sha256((package/name).read_bytes()).hexdigest()!=expected:
            raise PreparationRequired('Fixed3.1.9 source differs: '+name)
    saved=sys.argv
    try:
        sys.argv=['mob_recon']+list(native_args)
        args=recon.parse_args()
    finally:sys.argv=saved
    tree=ast.parse(Path(recon.__file__).read_text())
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    def assigns(n,name):return isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)
    start=next(i for i,n in enumerate(main.body) if assigns(n,'database_dir'))
    stop=next(i for i,n in enumerate(main.body) if assigns(n,'NCBI_PLASMID_TAXONOMY_FILE'))
    def refuse_initialization(logger,directory):
        status=Path(directory)/'status.txt'
        if not status.is_file() or status.stat().st_size==0:
            raise PreparationRequired('MOB default DB is not prepared: missing/empty status.txt; automatic initialization is prohibited')
    namespace=dict(os=os,args=args,default_database_dir=default_database_dir,
                   verify_init=refuse_initialization,logger=None)
    # Only the original resource path-selection statements are executed.
    # Its verify_init call becomes a check that never starts an initializer.
    exec(compile(ast.Module(body=main.body[start:stop+1],type_ignores=[]),str(recon.__file__),'exec'),namespace)
    names=['plasmid_ref_db','mob_ref','mash_db','replicon_ref','plasmid_meta',
           'repetitive_mask_file','mpf_ref','plasmid_orit','ETE3DBTAXAFILE',
           'LIT_PLASMID_TAXONOMY_FILE','NCBI_PLASMID_TAXONOMY_FILE']
    return args,{name:namespace[name] for name in names}


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


def check(native_args):
    args,paths=native_resource_paths(native_args)
    if args.filter_db or args.genome_filter_db_prefix:
        raise PreparationRequired('Optional filter DB/prefix readiness has not been implemented; original native support remains pending validation')
    missing=[name for name,path in paths.items() if not Path(path).is_file() or Path(path).stat().st_size==0]
    if missing:raise PreparationRequired('Required prepared resources missing/empty: '+','.join(missing))
    version=taxonomy_schema(paths['ETE3DBTAXAFILE'])
    return dict(tool='MOB-suite',version='3.1.9',preparation_presence_checks=True,
                taxonomy_schema_version=version,selected_paths=paths,
                scope='Read-only standalone preparation candidate only. No native science/init/download, full DB validity/cache identity/optional filter or nonviral provenance certification.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('native_args',nargs=argparse.REMAINDER)
    args=parser.parse_args();native=args.native_args[1:] if args.native_args[:1]==['--'] else args.native_args
    try:result=check(native)
    except (PreparationRequired,OSError) as error:parser.exit(2,str(error)+'\n')
    text=json.dumps(result,sort_keys=True)+'\n'
    if args.output:args.output.write_text(text)
    else:print(text,end='')


if __name__=='__main__':main()
