#!/usr/bin/env python3
"""ABRicate routing only: explicit CLI observer, no database search/biological calls."""
from pathlib import Path
import csv,hashlib,json,os,subprocess,shutil,tempfile,argparse

OBSERVER = '''#!/usr/bin/env python3
# Interface observer only; no ABRicate database search or biological result.
from pathlib import Path
import sys,hashlib
if '--version' in sys.argv:
 print('abricate 1.0.1');raise SystemExit()
args=sys.argv[1:];fasta=Path(args[0]);db=args[args.index('--db')+1]
print('#INTERFACE_OBSERVER\tINPUT_SHA256\tDATABASE')
print(str(fasta)+'\t'+hashlib.sha256(fasta.read_bytes()).hexdigest()+'\t'+db)
'''

def run_checks(base):
    root=Path(__file__).resolve().parents[1];base=Path(base).resolve()
    scripts=base/'observer-bin';scripts.mkdir(exist_ok=True)
    observer=scripts/'abricate';observer.write_text(OBSERVER);observer.chmod(0o755)
    fixture=base/'fixtures';fixture.mkdir(exist_ok=True)
    for sid,seq in [('S1','ACGTTGCA'*10),('S.2','GGCCAATT'*15)]:
     (fixture/f'{sid}.fasta').write_text(f'>{sid}_contig\n{seq}\n')
    config=base/'config';config.write_text(f"includeConfig '{root}/conf/nfcore_downstream.config'\nparams.typing_tools = []\nparams.typing_optional_tools = []\nparams.annotation_tools = []\nparams.annotation_optional_tools = []\nparams.plasmid_binning_tools = []\nparams.empty_plasmids = false\nparams.abricate_db = 'card'\nparams.publish_dir_mode = 'copy'\nprocess.executor = 'local'\nprocess.cpus = 1\nprocess.memory = '1 GB'\nconda.enabled = false\ndocker.enabled = false\nsingularity.enabled = false\n")
    cases=[('disabled',{},False),('main',{'annotation_tools':['abricate']},True),('optional',{'annotation_optional_tools':['abricate']},True),('both',{'annotation_tools':['abricate'],'annotation_optional_tools':['abricate']},True),('trimmed',{'annotation_optional_tools':[' abricate ']},True),('empty',{'annotation_optional_tools':['abricate'],'empty_plasmids':True},False)]
    runs=[]
    for case,extra,enabled in cases:
     p=base/case;p.mkdir(exist_ok=True);params={'fixture_dir':str(fixture),'outdir':str(p/'out'),**extra};(p/'params.json').write_text(json.dumps(params))
     command=[shutil.which('nextflow') or 'nextflow','-C',str(config),'run',str(root/'tests/nextflow/abricate_selection.nf'),'-params-file',str(p/'params.json'),'-work-dir',str(p/'work'),'-with-trace',str(p/'trace.tsv'),'-ansi-log','false'];env=os.environ.copy();env['PATH']=str(scripts)+':'+env['PATH'];r=subprocess.run(command,env=env,text=True,capture_output=True);(p/'stdout.log').write_text(r.stdout);(p/'stderr.log').write_text(r.stderr)
     tasks=list(csv.DictReader((p/'trace.tsv').open(),delimiter='\t')) if (p/'trace.tsv').exists() else [];reports=list((p/'out/08_annotation/abricate').glob('*.txt'))
     checks={'workflow_success':r.returncode==0,'task_count':len(tasks)==(2 if enabled else 0),'only_abricate':all('ABRICATE' in t['name'] and t['status']=='COMPLETED' and t['exit']=='0' for t in tasks),'report_count':len(reports)==(2 if enabled else 0)}
     if enabled:
      checks['sample_prefixes']={f.name for f in reports}=={'S1.card.txt','S.2.card.txt'}
      checks['input_provenance']=all((p/'out/08_annotation/abricate'/f'{sid}.card.txt').exists() and (p/'out/08_annotation/abricate'/f'{sid}.card.txt').read_text()==f'#INTERFACE_OBSERVER\tINPUT_SHA256\tDATABASE\n{sid}.card.fasta\t'+hashlib.sha256((fixture/f'{sid}.fasta').read_bytes()).hexdigest()+'\tcard\n' for sid in ['S1','S.2'])
     runs.append({'case':case,'command':command,'exit':r.returncode,'checks':checks,'tasks':tasks});print(case,checks,flush=True)
     receipt={'runs':runs,'pass':all(all(x['checks'].values()) for x in runs),'source_sha256':{f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in ['subworkflows/plasmid_downstream.nf','modules/nf-core/abricate/run/main.nf','conf/nfcore_downstream.config','lib/tool_selection.nf']},'limitations':['native original workflow/module, explicit CLI observer','not real ABRicate/CARD search, not P3 or annotation accuracy, not full platform E2E']};(base/'run.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt['pass']


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir',default=None)
    args=parser.parse_args()
    base=Path(args.work_dir or tempfile.mkdtemp(prefix='abricate-routing-'))
    base.mkdir(parents=True,exist_ok=True)
    print('ABRicate routing interface observer only; no biological search. Artifacts:',base)
    raise SystemExit(0 if run_checks(base) else 1)
