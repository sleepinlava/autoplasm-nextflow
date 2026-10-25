#!/usr/bin/env python3
"""Native resume controls: an analysis executable/helper is part of task identity.

Only disposable project copies change. A deliberately different private formula
provides a visible stale-cache oracle; production code is never altered here.
"""
import argparse,csv,hashlib,json,math,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--work-dir',type=Path,required=True);parser.add_argument('--before-dir',type=Path,required=True);a=parser.parse_args();base=a.work_dir.resolve();base.mkdir(parents=True,exist_ok=False);sources=['modules/cross_sample/diversity.nf','bin/diversity.R','bin/statistics_input_contract.R','tests/run_statistics_cache.py'];hashes={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sources};runs=[]
    for old in [True,False]:
        project=base/('before' if old else 'current');(project/'modules/cross_sample').mkdir(parents=True);(project/'bin').mkdir()
        module=a.before_dir.resolve()/'modules/cross_sample/diversity.nf' if old else ROOT/'modules/cross_sample/diversity.nf';shutil.copy2(module,project/'modules/cross_sample/diversity.nf')
        for name in ['diversity.R','statistics_input_contract.R']:shutil.copy2(ROOT/'bin'/name,project/'bin'/name)
        ab=project/'counts.tsv';ab.write_text('sample_id\tcontig_id\tcoverage\nS1\tF1\t1\nS1\tF2\t1\nS2\tF1\t3\nS2\tF2\t1\n');meta=project/'metadata.tsv';meta.write_text('sample_id\tgroup\nS1\tA\nS2\tB\n');(project/'main.nf').write_text("nextflow.enable.dsl=2\ninclude { DIVERSITY } from './modules/cross_sample/diversity'\nworkflow { DIVERSITY(file('"+str(ab)+"'),file('"+str(meta)+"')"+("" if old else ",[file('"+str(project/'bin/diversity.R')+"'),file('"+str(project/'bin/statistics_input_contract.R')+"')]")+") }\n")
        config=project/'native.config';config.write_text(f"params.outdir='{project}/out'\nparams.publish_dir_mode='copy'\nprocess.executor='local'\nprocess.cpus=1\nprocess.memory='1 GB'\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\ntrace.fields='task_id,hash,name,status,exit,workdir'\n");env=os.environ.copy();env['PATH']=str(project/'bin')+':'+env['PATH'];steps=['first','changed-helper'] if old else ['first','unchanged','changed-helper','changed-analysis']
        for step in steps:
            if step=='changed-helper':
                helper=project/'bin/statistics_input_contract.R';helper.write_text(helper.read_text()+'\n# Deliberate private dependency formula control; never production.\ndiversity <- function(x,index="shannon",...) { if(index=="shannon") 0.125 else vegan::diversity(x,index=index,...) }\n')
            if step=='changed-analysis':
                script=project/'bin/diversity.R';text=script.read_text();assert 'index="shannon"' in text;text=text.replace('index="shannon"','index="simpson"');script.write_text(text)
            trace=project/(step+'.trace.tsv');cmd=[shutil.which('nextflow') or 'nextflow','-C',str(config),'run',str(project/'main.nf'),'-work-dir',str(project/'work'),'-with-trace',str(trace),'-ansi-log','false']
            if step!='first':cmd.append('-resume')
            r=subprocess.run(cmd,cwd=project,text=True,capture_output=True,env=env);(project/(step+'.console.log')).write_text(r.stdout+r.stderr);assert r.returncode==0,r.stdout+r.stderr;tasks=list(csv.DictReader(trace.open(),delimiter='\t'));assert len(tasks)==1
            expected='CACHED' if (old and step=='changed-helper') or (not old and step=='unchanged') else 'COMPLETED';assert tasks[0]['status']==expected,tasks
            rows=list(csv.DictReader((project/'out/11_diversity/diversity_metrics.tsv').open(),delimiter='\t'));value=float(next(x['value'] for x in rows if x['sample_id']=='S1' and x['metric']=='shannon'));target=(.5 if step=='changed-analysis' else .125) if not old and step in ['changed-helper','changed-analysis'] else math.log(2);assert math.isclose(value,target,abs_tol=1e-6)
            if old and step=='changed-helper':
                direct=[ 'Rscript',str(project/'bin/diversity.R'),'--abundance',str(ab),'--metadata',str(meta),'--out-metrics',str(project/'direct.tsv'),'--out-beta',str(project/'direct-beta.tsv') ];dr=subprocess.run(direct,text=True,capture_output=True,check=True,env=env);actual=float(next(x['value'] for x in csv.DictReader((project/'direct.tsv').open(),delimiter='\t') if x['sample_id']=='S1' and x['metric']=='shannon'));assert math.isclose(actual,.125,abs_tol=1e-6);assert actual!=value
            runs.append({'before':old,'step':step,'command':cmd,'exit':r.returncode,'tasks':tasks,'S1_output_named_shannon':value,'deliberate_private_formula':'helper shannon0.125 after changed-helper; analysis uses Simpson after changed-analysis'})
    assert hashes=={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sources};(base/'run.json').write_text(json.dumps({'pass':True,'runs':runs,'source_sha256':hashes,'limitations':['only disposable project code changed; formula substitution is a visible cache-control fault, not a production algorithm change','native R/Nextflow cache behavior, no nf-test/image/remote executor/model accuracy certification','declared path inputs bind the analysis script and helper to task identity; this old-module/current-helper counterexample tests a regression introduced during the repair, not a historical helper in the original baseline; other wrappers are not certified']},indent=2)+'\n');print('PASS6 trace entries: old stale formula cached, current unchanged cached/helper and formula changes recomputed')


if __name__=='__main__':main()
