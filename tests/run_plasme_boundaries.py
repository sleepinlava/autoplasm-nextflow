#!/usr/bin/env python3
"""Real fixed PLASMe function boundaries; tiny BLAST reference, no model inference."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work-dir',type=Path,required=True)
    p.add_argument('--source-dir',type=Path,required=True)
    p.add_argument('--python',type=Path,required=True)
    a=p.parse_args();base=a.work_dir.resolve();base.mkdir(parents=True,exist_ok=False)
    source=a.source_dir.resolve();python=a.python.resolve()
    spec=importlib.util.spec_from_file_location('runtime',ROOT/'bin/plasme_runtime.py')
    runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
    sources={str(q):sha(q) for q in [source/'PLASMe.py',source/'bio_script.py',ROOT/'bin/plasme_runtime.py',Path(__file__).resolve()]}
    fixture=base/'fixture';fixture.mkdir()
    rng=random.Random(240067)
    (fixture/'reference.fna').write_text('>R\n'+''.join(rng.choices('ACGT',k=6000))+'\n')
    (fixture/'query.fna').write_text('>no_hit\n'+'N'*1000+'\n')
    (fixture/'worker.fna').write_text('>worker\n'+'ACGT'*500+'\n')
    (fixture/'taxonomy.tsv').write_text('R Enterobacterales\n')
    (fixture/'overlap.tsv').write_text('R\n')
    env={**os.environ,'PATH':str(python.parent)+os.pathsep+os.environ['PATH']}
    result=subprocess.run([str(python.parent/'makeblastdb'),'-in',str(fixture/'reference.fna'),'-dbtype','nucl','-out',str(fixture/'reference')],env=env,capture_output=True,text=True)
    (base/'makeblastdb.log').write_text(result.stdout+result.stderr);assert result.returncode==0
    shim=fixture/'shim';shim.mkdir()
    fake=shim/'prodigal'
    fake.write_text('#!/usr/bin/env python3\nfrom pathlib import Path\nimport sys\na=sys.argv\n'
                    'Path(a[a.index("-a")+1]).write_text(">worker_1\\nMFAKEPARTIAL*\\n")\n'
                    'Path(a[a.index("-o")+1]).write_text("# explicit partial-output failure observer\\n")\n'
                    'raise SystemExit(7)\n')
    fake.chmod(0o755)
    cases=[('before-no-hit',False,'predict',False),('fixed-no-hit',True,'predict',False),
           ('fixed-bad-db',True,'predict',True),('before-worker-failure',False,'worker',False),
           ('fixed-worker-failure',True,'worker',False)]
    runs=[]
    for name,patched,mode,bad_db in cases:
        d=base/name;d.mkdir()
        program=source/'PLASMe.py';patch={'applied':False}
        if patched:
            previous=Path.cwd()
            try:
                os.chdir(d);program,patch=runtime.prepare_program(source);program=program.resolve()
            finally:os.chdir(previous)
            assert patch['applied']
        if mode=='predict':
            db=fixture/('missing-db' if bad_db else 'reference')
            script=('from pathlib import Path\nimport sys\nsys.path.insert(0,'+repr(str(program.parent))+')\nimport PLASMe\n'
                    'PLASMe.predict(contig_path='+repr(str(fixture/'query.fna'))+',ref_plas_db_path='+repr(str(db))+',ref_tax_path='+repr(str(fixture/'taxonomy.tsv'))+
                    ',temp_dir="temp",out_path="candidates.csv",ref_ol_path='+repr(str(fixture/'overlap.tsv'))+',db_dir="no_models_exist",min_cov=0.0,num_threads=1)\n'
                    'PLASMe.plasme_output("candidates.csv","temp/blastn.csv",'+repr(str(fixture/'query.fna'))+',0.9,0.9,0.5,"result.fasta")\n')
            caseenv=env
        else:
            shutil.copyfile(fixture/'worker.fna',d/'worker.fna')
            script='import sys\nsys.path.insert(0,'+repr(str(program.parent))+')\nimport bio_script\nbio_script.run_multi_prodigal("worker.fna",threads=1)\n'
            caseenv={**env,'PATH':str(shim)+os.pathsep+env['PATH']}
        (d/'call.py').write_text(script)
        result=subprocess.run([str(python),str(d/'call.py')],cwd=d,env=caseenv,capture_output=True,text=True)
        (d/'stdout.log').write_text(result.stdout);(d/'stderr.log').write_text(result.stderr)
        if name=='before-no-hit':assert result.returncode!=0 and 'range() arg 3 must not be zero' in result.stderr
        elif name=='fixed-no-hit':
            assert result.returncode==0,result.stderr
            assert (d/'result.fasta').read_bytes()==b''
            assert (d/'result.fasta_report.csv').read_text()=='contig\tlength\treference\torder\tevidence\tscore\tamb_region\n'
            assert (d/'candidates.csv').read_text()=='order,query,identity,coverage,PLASMe,overlap\n'
        elif name=='before-worker-failure':
            assert result.returncode==0,result.stderr
            assert 'MFAKEPARTIAL' in (d/'worker.fna.aa').read_text()
        else:
            assert result.returncode!=0 and 'CalledProcessError' in result.stderr,result.stderr
            if bad_db:assert not (d/'candidates.csv').exists()
        runs.append({'case':name,'exit':result.returncode,'patch':patch,'external_scope':'real BLAST' if mode=='predict' else 'explicit partial-output Prodigal failure observer'})
        assert sources=={name:sha(Path(name)) for name in sources}
        (base/'run.json').write_text(json.dumps({'pass':len(runs)==len(cases),'runs':runs,'source_sha256':sources,
          'limitations':['Tiny unit-boundary reference only; not the full PLASMe database or any model/biological classification validation',
                         'Prodigal failure is explicitly simulated; BLAST no-hit and invalid DB use real pinned2.13.0']},indent=2)+'\n')
        print('PASS',name,flush=True)


if __name__=='__main__':main()
