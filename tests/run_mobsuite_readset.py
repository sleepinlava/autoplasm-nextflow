#!/usr/bin/env python3
"""Execute fixed3.1.9 source parser/path-selection slices without scientific dependencies.

Explicit verify_init observer records calls; never imports MOB, initializes a
DB, creates taxonomy data or invokes a scientific executable. Not a native
MOB installation, production resource probe or classification acceptance.
"""
import argparse
import ast
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def run(source,output):
    output.mkdir(parents=True,exist_ok=False)
    lock=json.loads((ROOT/'tests/mobsuite-readset.lock.json').read_text())
    assert all(sha(source/p)==s for p,s in lock['files_sha256'].items())
    tree=ast.parse((source/'mob_suite/mob_recon.py').read_text())
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse_args')
    constants=ast.parse((source/'mob_suite/constants.py').read_text())
    assignment=next(n for n in constants.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='default_database_dir' for t in n.targets))
    version={};exec(compile(ast.parse((source/'mob_suite/version.py').read_text()),'native_version','exec'),version)
    namespace=dict(os=os,__file__=str(source/'mob_suite/constants.py'),__version__=version['__version__'],
                   ArgumentParser=argparse.ArgumentParser,ArgumentDefaultsHelpFormatter=argparse.ArgumentDefaultsHelpFormatter,
                   RawDescriptionHelpFormatter=argparse.RawDescriptionHelpFormatter)
    exec(compile(ast.Module(body=[assignment,function],type_ignores=[]),'native_parser','exec'),namespace)
    default=namespace['default_database_dir'];main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    def target(n,name):return isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)
    start=next(i for i,n in enumerate(main.body) if target(n,'database_dir'))
    stop=next(i for i,n in enumerate(main.body) if target(n,'NCBI_PLASMID_TAXONOMY_FILE'))
    slice_code=compile(ast.Module(body=main.body[start:stop+1],type_ignores=[]),'native_path_selection','exec')
    resources=['plasmid_ref_db','mob_ref','mash_db','replicon_ref','plasmid_meta','repetitive_mask_file','mpf_ref','plasmid_orit','ETE3DBTAXAFILE','LIT_PLASMID_TAXONOMY_FILE','NCBI_PLASMID_TAXONOMY_FILE']
    cases=[]
    def select(label,extra):
        saved=sys.argv
        try:
            sys.argv=['mob_recon','-i','NO_SEQUENCE_OPENED.fasta','-o','NO_OUTPUT_CREATED',*extra]
            args=namespace['parse_args']()
        finally:sys.argv=saved
        calls=[]
        cfg=dict(namespace,args=args,logger=None,verify_init=lambda logger,path:calls.append(path))
        exec(slice_code,cfg)
        record=dict(case=label,arguments=vars(args),selected_paths={n:cfg[n] for n in resources},verify_init_observer_calls=calls)
        cases.append(record);return record
    baseline=select('default',[])
    assert baseline['verify_init_observer_calls']==[default]
    assert all(p.startswith(default+'/') for p in baseline['selected_paths'].values())
    for option,variable in [('--plasmid_db','plasmid_ref_db'),('--plasmid_mob','mob_ref'),('--plasmid_mash_db','mash_db'),('--plasmid_replicons','replicon_ref'),('--plasmid_meta','plasmid_meta'),('--repetitive_mask','repetitive_mask_file'),('--plasmid_mpf','mpf_ref'),('--plasmid_orit','plasmid_orit')]:
        external='/EXTERNAL_CONTROL_NO_FILE/'+variable
        row=select('default-override-'+variable,[option,external]);assert row['selected_paths'][variable]==external and row['verify_init_observer_calls']==[default]
        row=select('custom-directory-overrides-'+variable,['-d','/CUSTOM_CONTROL_NO_FILES',option,external]);assert row['selected_paths'][variable].startswith('/CUSTOM_CONTROL_NO_FILES/') and not row['verify_init_observer_calls'];assert row['selected_paths'][variable]!=external
    relative=select('relative-custom-directory',['-d','RELATIVE_CONTROL_NO_FILES'])
    assert all(p.startswith(os.path.abspath('RELATIVE_CONTROL_NO_FILES')+'/') for p in relative['selected_paths'].values())
    optional=select('optional-genome-and-filter-prefixes',['-b','/FILTER_CONTROL_NO_FILE','-g','/GENOME_CONTROL_NO_FILE'])
    assert optional['arguments']['filter_db']=='/FILTER_CONTROL_NO_FILE' and optional['arguments']['genome_filter_db_prefix']=='/GENOME_CONTROL_NO_FILE'
    with contextlib.redirect_stderr(io.StringIO()):
        try:select('invalid-option',['--not-a-mob-option'])
        except SystemExit as error:assert error.code==2
        else:raise AssertionError('Native parser accepted unknown option')
    result=dict(pass_bounded_source_checks=True,formal_acceptance=False,source_commit=lock['source_commit'],cases=cases,positive_path_cases=len(cases),unknown_option_refused=True,source_sha256={str(Path(__file__).relative_to(ROOT)):sha(Path(__file__)),'tests/mobsuite-readset.lock.json':sha(ROOT/'tests/mobsuite-readset.lock.json')},scope='Original fixed3.1.9 argparse/constants/main DB-selection AST slices only, verify_init explicitly observed and never executed.19source path cases and unknown-option negative; no MOB environment, DB/sequence/taxonomy/model download, native scientific invocation, resource-cache integration or biological certification.')
    (output/'run.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(cases=len(cases),unknown_option_refused=True,scope='source-bound parser/path-selection only')))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.source.resolve(),a.output.resolve())
