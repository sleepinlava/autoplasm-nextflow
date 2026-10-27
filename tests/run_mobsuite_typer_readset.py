#!/usr/bin/env python3
"""Actual installed MOB typer parser/DB-path slice; no main/science/init execution."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]


def run(output):
    import mob_suite.mob_typer as typer
    from mob_suite.constants import default_database_dir
    output.mkdir(parents=True,exist_ok=False)
    source=Path(typer.__file__)
    code=ast.parse(source.read_text())
    main=next(n for n in code.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    def assigned(n,name):return isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)
    statements=[]
    for node in main.body:
        if any(assigned(node,name) for name in ['database_dir','ETE3DBTAXAFILE','LIT_PLASMID_TAXONOMY_FILE','NCBI_PLASMID_TAXONOMY_FILE']):statements.append(node)
        elif isinstance(node,ast.If) and ast.unparse(node.test)=='database_dir == default_database_dir':statements.append(node)
    assert len(statements)==5
    saved=sys.argv
    try:
        sys.argv=['mob_typer','--multi','--infile','NO_SEQUENCE_OPENED.fasta','--out_file','NO_REPORT_CREATED.txt']
        args=typer.parse_args()
    finally:sys.argv=saved
    calls=[]
    namespace=dict(os=os,args=args,default_database_dir=default_database_dir,logger=None,verify_init=lambda logger,path:calls.append(path))
    exec(compile(ast.Module(body=statements,type_ignores=[]),str(source),'exec'),namespace)
    assert calls==[default_database_dir]
    names=['mob_ref','mash_db','replicon_ref','plasmid_meta','mpf_ref','plasmid_orit','repetitive_mask_file','ETE3DBTAXAFILE','LIT_PLASMID_TAXONOMY_FILE']
    paths={name:namespace[name] for name in names};assert all(str(p).startswith(default_database_dir+'/') for p in paths.values())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    project_sources=['tests/run_mobsuite_typer_readset.py','modules/nf-core/mobsuite/typer/main.nf','subworkflows/plasmid_downstream.nf','lib/resource_inputs.nf']
    result=dict(pass_source_readset_check=True,formal_acceptance=False,installed_typer_source_sha256=sha(source),version=typer.__version__,parsed_arguments=vars(args),selected_environment_paths=paths,verify_init_observer_calls=calls,source_sha256={p:sha(ROOT/p) for p in project_sources},new_resource_pair='MOB_TYPER environment-default database when optional explicit inputs absent',scope='Real installed parse_args and original5DB-selection AST statements only; verify_init explicit observer, not called for real.Production passes seven empty optional files and absent directory identity by default; those identities cannot represent changing environment resources. No scientific main, temp directory/report/input sequence/download or DB initialization.Explicit directory mode stays separate; default implicit pair pending.')
    (output/'run.json').write_text(json.dumps(result,indent=2)+'\n');print('Confirmed actual MOB typer default environment paths/init branch; no science/init executed')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.output.resolve())
