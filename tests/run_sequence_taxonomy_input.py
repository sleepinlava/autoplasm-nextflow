#!/usr/bin/env python3
"""Original LINK_SEQUENCE taxonomy filename collision: frozen before and repaired nodes.

Controlled self-match DNA; taxonomy strings are interface markers, not host truth.
"""
import argparse,csv,hashlib,json,os,random,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--work-dir',type=Path,required=True);parser.add_argument('--before-dir',type=Path,required=True);args=parser.parse_args();base=args.work_dir.resolve();base.mkdir(parents=True,exist_ok=False);sources=['modules/linking/sequence.nf','bin/sequence_similarity_link.R','tests/run_sequence_taxonomy_input.py'];source_sha={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sources};runs=[]
    sequence=''.join(random.Random(5802026).choices('ACGT',k=1800))
    for name,old,multiple in [('before',True,False),('after-single',False,False),('after-two-domains',False,True)]:
        d=base/name;d.mkdir();fixture=d/'fixture';mag=fixture/'bins';mag.mkdir(parents=True);(fixture/'plasmids.fa').write_text('>p1\n'+sequence+'\n');(mag/'host1.fa').write_text('>c1\n'+sequence+'\n');(fixture/'taxonomy.tsv').write_text('user_genome\tclassification\nhost1.fa\td__MARKER_ONE\n');tax=[fixture/'taxonomy.tsv']
        if multiple:
            (mag/'host2.fa').write_text('>c2\n'+sequence+'\n');(fixture/'second').mkdir();(fixture/'second/taxonomy.tsv').write_text('user_genome\tclassification\nhost2.fa\td__MARKER_TWO\n');tax.append(fixture/'second/taxonomy.tsv')
        hashes={str(p.relative_to(fixture)):hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.rglob('*') if p.is_file()};(d/'inputs-before.json').write_text(json.dumps(hashes,indent=2)+'\n')
        module=args.before_dir.resolve()/'modules/linking/sequence' if old else ROOT/'modules/linking/sequence';probe=d/'probe.nf';probe.write_text(f"nextflow.enable.dsl=2\ninclude {{ LINK_SEQUENCE }} from '{module}'\nworkflow {{\nLINK_SEQUENCE(Channel.of(tuple([id:'S',group:'kept'],file('{fixture}/plasmids.fa'),[file('{mag}')],["+','.join("file('"+str(t)+"')" for t in tax)+"])))\n}\n")
        config=d/'native.config';config.write_text(f"params.outdir='{d}/out'\nparams.publish_dir_mode='copy'\nparams.link_min_similarity=0.7\nprocess.executor='local'\nprocess.cpus=1\nprocess.memory='1 GB'\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\ntrace.fields='task_id,hash,name,status,exit,workdir'\n")
        cmd=[shutil.which('nextflow') or 'nextflow','-C',str(config),'run',str(probe),'-work-dir',str(d/'work'),'-with-trace',str(d/'trace.tsv'),'-ansi-log','false'];env=os.environ.copy();env['PATH']=str(args.before_dir.resolve()/'bin' if old else ROOT/'bin')+':'+env['PATH'];r=subprocess.run(cmd,text=True,capture_output=True,env=env);(d/'console.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stdout+r.stderr
        tasks=list(csv.DictReader((d/'trace.tsv').open(),delimiter='\t'));assert len(tasks)==1 and tasks[0]['status']=='COMPLETED' and tasks[0]['exit']=='0';after={str(p.relative_to(fixture)):hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.rglob('*') if p.is_file()};links=list(csv.DictReader((d/'out/07_host_prediction/linking/sequence/S.sequence_links.tsv').open(),delimiter='\t'));assert len(links)==(1 if old else 0)
        if old:
            assert (fixture/'taxonomy.tsv').stat().st_size==0 and after['taxonomy.tsv']!=hashes['taxonomy.tsv'];assert 'taxonomy=NA;' in links[0]['supporting_data']
        else:
            assert after==hashes,'Source input mutation';expected={'host1':'d__MARKER_ONE','host2':'d__MARKER_TWO'}
            scores=list(csv.DictReader((d/'out/07_host_prediction/linking/sequence/S.sequence_scores.tsv').open(),delimiter='\t'));assert len(scores)==len(tax)
            for row in scores:assert row['host_taxonomy']==expected[row['host_id']] and row['association_status']=='disabled_uncalibrated'
        runs.append({'case':name,'command':cmd,'exit':r.returncode,'tasks':tasks,'before_hashes':hashes,'after_hashes':after,'links':links,'source_mutation_expected':old})
    assert source_sha=={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sources};(base/'run.json').write_text(json.dumps({'pass':True,'runs':runs,'source_sha256':source_sha,'limitations':['before intentionally mutates disposable fixture only; exact frozen module and R definitions','self-match controlled interface DNA/taxonomy labels; not known-host or taxonomy biological benchmark','native local R/Biostrings; image/remote executor/nf-test framework not executed']},indent=2)+'\n');print('PASS frozen before1/current2 native nodes; input identity and exact taxonomy labels')


if __name__=='__main__':main()
