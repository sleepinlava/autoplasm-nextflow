#!/usr/bin/env python3
"""Real pinned ANI/graph/HMMER boundaries; not a complete classification benchmark."""
import argparse
import ast
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pathlib
import pickle
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def function(path,name,namespace):
    tree=ast.parse(path.read_text())
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),namespace)
    return namespace[name]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['work-dir','installation','macsyfinder']:
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();base=a.work_dir.resolve();base.mkdir(parents=True,exist_ok=False)
    install=a.installation.resolve();old=install/'bin/copla.py'
    spec=importlib.util.spec_from_file_location('copla_adapter',ROOT/'bin/run_copla_candidates.py')
    adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
    program=base/'fixed';program.mkdir()
    patch=adapter.prepare_program(install,program,a.macsyfinder,2);assert patch['applied']
    env={**os.environ,'LD_LIBRARY_PATH':str(install/'lib'),'COPLA_THREADS':'2'}
    source=install/'test/NZ_CP028167.1.fna';reference=install/'databases/Copla_RS84/NZ_CP015977.1.fna'
    runs=[]
    def call(name,command,cwd,case_env=None):
        d=base/name;d.mkdir(exist_ok=True)
        r=subprocess.run(command,cwd=cwd,env=case_env or env,capture_output=True,text=True)
        (d/'stdout.log').write_text(r.stdout);(d/'stderr.log').write_text(r.stderr)
        return r
    pair=[]
    for name,ruby in [('original-pair',install/'bin/ani.rb'),('fixed-pair',program/'bin/ani.rb')]:
        out=base/(name+'.tsv')
        command=['ruby',str(ruby),'-1',str(source),'-2',str(reference),'-T',str(out),'-n','80','-w','1000','-s','200','-d','3','-t','1','-q']
        result=call(name,command,base);assert result.returncode==0 and out.is_file(),result.stderr
        pair.append(out.read_bytes());runs.append({'case':name,'command':command,'exit':result.returncode,'ANI_table':out.read_text()})
    assert pair[0]==pair[1] and 99<float(pair[0].split(b'\t')[0])<=100
    # Actual native ANI row, passed to actual functions and the complete graph.
    import graph_tool.all as gt
    with (install/'databases/Copla_RS84/RS84f_sHSBM.pickle').open('rb') as f:graph,state=pickle.load(f)
    actual=base/'actual-ani.tsv';actual.write_text('query.fna\tNZ_CP015977.1.fna\t'+pair[0].decode())
    original_graph=graph.copy();q=original_graph.add_vertex();original_graph.vp.AccessionVersion[q]='<Query>'
    before=function(old,'insert_ani_edges',{'v_qry':q})
    before(original_graph,str(actual))
    neighbors=list(q.all_neighbors())
    assert len(neighbors)==1 and original_graph.vp.AccessionVersion[neighbors[0]]=='NZ_CP015977.1'
    runs.append({'case':'original-reference-parser','result':'already correct; inactive FastANI function was excluded from defect scope','native_ANI':str(actual)})
    fixed_graph=graph.copy();q=fixed_graph.add_vertex();fixed_graph.vp.AccessionVersion[q]='<Query>'
    after=function(program/'bin/copla.py','insert_ani_edges',{'v_qry':q,'pathlib':pathlib})
    after(fixed_graph,str(actual));neighbors=list(q.all_neighbors())
    assert len(neighbors)==1 and fixed_graph.vp.AccessionVersion[neighbors[0]]=='NZ_CP015977.1'
    runs.append({'case':'fixed-reference-parser','edge_reference':'NZ_CP015977.1','native_ANI':str(actual)})
    # Full archive includes29 references <=1000bp; fixed windows cannot assess them.
    short=install/'databases/Copla_RS84/NZ_CP019137.1.fna'
    short_out=base/'short.tsv'
    r=call('fixed-short',['ruby',str(program/'bin/ani.rb'),'-1',str(source),'-2',str(short),'-T',str(short_out),'-n','1','-w','1000','-s','200','-d','3','-t','1','-q'],base)
    assert r.returncode==0 and not short_out.exists()
    assert Path(str(short_out)+'.not_evaluable').read_text()=='no_informative_fragments\tseq2'
    runs.append({'case':'fixed-short-reference','exit':0,'status':'not_evaluable_no_fragments','scope':'fixed1000bp window, not an evaluated biological negative'})
    # A direct missing reference already fails while Perl reads its length.
    # Exercise the actual unchecked Ruby child instead, with valid real DNA
    # and a PATH which lacks BLAST executables (no simulated command output).
    isolated=base/'without-blast';isolated.mkdir()
    (isolated/'ruby').symlink_to(shutil.which('ruby'))
    perl=shutil.which('perl')
    for name,root,expected in [('original-worker',install,0),('fixed-worker',program,1)]:
        d=base/name;d.mkdir(exist_ok=True);query=d/'query.fna';shutil.copyfile(source,query)
        command=[perl,str(root/'bin/get_ani_identity_job.pl'),str(query),'33305',str(reference)]
        r=call(name,command,root,{**env,'PATH':str(isolated)})
        assert (r.returncode==0)==(expected==0)
        assert not (d/(reference.name+'.tsv')).exists()
        runs.append({'case':name,'command':command,'exit':r.returncode,'real_missing_BLAST_executables':True})
    # A missing real HMM database is an error, distinct from a legitimate no-hit.
    os.environ['COPLA_THREADS']='2';os.environ['PATH']=env['PATH']
    cwd=Path.cwd();os.chdir(base)
    try:
        globals_={'pathlib':pathlib,'subprocess':subprocess,'os':os}
        before=function(old,'run_mobscan',dict(globals_));after=function(program/'bin/copla.py','run_mobscan',dict(globals_))
        protein=install/'test/NZ_CP028167.1.faa'
        assert before(str(protein),'old-mob')=='-'
        try:after(str(protein),'new-mob')
        except subprocess.CalledProcessError as error:assert error.returncode!=0
        else:raise AssertionError('Missing HMM database became a negative result')
    finally:os.chdir(cwd)
    runs.extend([{'case':'original-MOB-missing-DB','result':'masked as negative'},
                 {'case':'fixed-MOB-missing-DB','result':'CalledProcessError'}])
    receipt={'pass':True,'runs':runs,'source_patch':patch,'source_adapter_sha256':adapter.sha(ROOT/'bin/run_copla_candidates.py'),
             'scope':'Real pinned ANI pair equivalence and short eligibility; full actual graph function parser; actual missing-BLAST Perl child and missing-HMM controls. No full classification or accuracy claim.'}
    (base/'run.json').write_text(json.dumps(receipt,indent=2)+'\n');print('PASS real ANI/graph/failure controls',len(runs),flush=True)


if __name__=='__main__':main()
