#!/usr/bin/env python3
"""Original GTDB module against actual2.7.2 parser/selection, no taxonomy model.

Requires an installed GTDB2.7.2 prefix and two real, already verified genome
FASTA inputs. Source bytes/DNA are the independent preservation oracle. A tiny
reference-name fixture and synthetic summary markers are explicitly observers.
"""
from module_harness import render_module_harness
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sequence_facts(data):
    records={};current=None
    for line in data.decode().splitlines():
        if line.startswith('>'):
            current=line[1:].split()[0];assert current not in records;records[current]=''
        elif line.strip():
            assert current is not None;records[current]+=line.strip()
    return {name:{'length':len(dna),'DNA_sha256':hashlib.sha256(dna.encode()).hexdigest()} for name,dna in records.items()}


def run(base,prefix,genomes,before):
    base.mkdir(parents=True)
    original={str(p):sha(p) for p in genomes};dna=[p.read_bytes() for p in genomes]
    fixtures=base/'fixtures';fixtures.mkdir()
    paths={}
    for name,payload in [('A.1.fa',dna[0]),('B.2.fa.gz',gzip.compress(dna[1],mtime=0)),
                         ('C.3.fna',dna[0]),('D.FASTA.GZ',gzip.compress(dna[1],mtime=0)),
                         ('same.fa',dna[0]),('same.fna.gz',gzip.compress(dna[1],mtime=0)),
                         ('corrupt.fa.gz',b'not gzip')]:
        path=fixtures/name;path.write_bytes(payload);paths[name]=str(path)
    db=fixtures/'reference_name_fixture';(db/'metadata').mkdir(parents=True);(db/'taxonomy').mkdir()
    (db/'metadata/metadata.txt').write_text('VERSION_DATA=EXPLICIT_INTERFACE_FIXTURE\n')
    (db/'taxonomy/gtdb_taxonomy.tsv').write_text('RS_GCF_000001405.40\tNOT_A_TAXONOMY_DATABASE\n')
    observers=base/'observer-bin';observers.mkdir();observer=observers/'gtdbtk'
    observer.write_text('#!'+str(prefix/'bin/python3')+'\n'+'\n'.join((ROOT/'tests/gtdb_input_observer.py').read_text().splitlines()[1:])+'\n');observer.chmod(0o755)
    records=[{'id':'S1','bins':[paths['A.1.fa'],paths['B.2.fa.gz'],paths['C.3.fna']]},
             {'id':'S.2','bins':[paths['D.FASTA.GZ']]}]
    expected={'S1':{'A.1':dna[0],'B.2':dna[1],'C.3':dna[0]},'S.2':{'D':dna[1]}}
    runs=[]
    def execute(name,selected=records,extra=None,module=None,failure=None,resume=False):
        folder=base/name;folder.mkdir(exist_ok=resume)
        config=folder/'config'
        if not resume:
            config.write_text('includeConfig '+repr(str(ROOT/'conf/nfcore_mag.config'))+'\n'
                "params.publish_dir_mode='copy'\nprocess.executor='local'\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\n"
                "trace { enabled=true; fields='task_id,hash,native_id,name,status,exit,workdir'; overwrite=true }\n"
                "process { withName:'GTDBTK' { cpus=1; memory='512 MB'; "+("ext.args="+repr(extra) if extra is not None else '')+" } }\n")
            params={'records':selected,'gtdbtk_db':str(db),'outdir':str(folder/'out')}
            (folder/'params.json').write_text(json.dumps(params))
        workflow=ROOT/'tests/nextflow/gtdb_inputs.nf'
        if module:
            workflow=folder/'module_probe.nf'
            if not resume:workflow.write_text(render_module_harness(ROOT/'tests/nextflow/gtdb_inputs.nf', '../../modules/nf-core/gtdbtk/classifywf/main', module, 'normalize_gtdb_bins.py'))
        trace=folder/('trace-resume.tsv' if resume else 'trace.tsv')
        command=[str(ROOT/'results/tool-audit/runtime/bin/nextflow'),'-C',str(config),'run',str(workflow),'-params-file',str(folder/'params.json'),'-work-dir',str(folder/'work'),'-with-trace',str(trace),'-ansi-log','false']
        if resume:command+=['-resume']
        env={**os.environ,'PATH':str(observers)+':'+str(prefix/'bin')+':'+os.environ['PATH']}
        if failure=='observer':env['GTDB_INPUT_OBSERVER_FAIL']='1'
        result=subprocess.run(command,capture_output=True,text=True,env=env)
        suffix='-resume' if resume else ''
        (folder/('stdout'+suffix+'.log')).write_text(result.stdout);(folder/('stderr'+suffix+'.log')).write_text(result.stderr)
        tasks=list(csv.DictReader(trace.open(),delimiter='\t')) if trace.exists() else []
        outputs=folder/'out/07_host_prediction/mag/gtdbtk'
        checks={}
        if failure in ['duplicate','gzip','observer','old_no_extension','obsolete_option']:
            checks['failure_not_hidden']=result.returncode!=0 and any(t['status']=='FAILED' for t in tasks)
            errors='\n'.join(p.read_text() for p in (folder/'work').rglob('.command.err'))
            diagnostic={'duplicate':'Duplicate GTDB-Tk genome ID','gzip':'Invalid gzip GTDB-Tk bin','observer':'EXPLICIT_GTDB_INPUT_OBSERVER_FAILURE','old_no_extension':'No genomes found in directory','obsolete_option':'unrecognized arguments: --skip_ani_screen'}[failure]
            checks['diagnostic_from_failed_task']=diagnostic in errors
            checks['no_published_partial_result']=not [p for p in outputs.rglob('*') if p.is_file()]
            if failure in ['duplicate','gzip']:
                checks['failed_before_native_selector']=not any('NATIVE_GTDB_SELECTION_REACHED' in p.read_text() for p in (folder/'work').rglob('.command.out'))
        else:
            checks['success']=result.returncode==0
            checks['task_count']=len(tasks)==len(selected)
            checks['task_states']=all(t['status']==('CACHED' if resume else 'COMPLETED') for t in tasks)
            for row in selected:
                sid=row['id'];selection=outputs/sid/'input_selection.json'
                if not selection.is_file():checks[sid+'_selection_present']=False;continue
                observed=json.loads(selection.read_text())
                actual={v['genome_id']:v for v in observed['genomes']}
                wanted=expected[sid]
                if failure=='old_partial_selection':
                    checks[sid+'_old_dropped_bins_reproduced']=set(actual)=={'C.3'} and set(actual)!=set(wanted)
                    continue
                checks[sid+'_all_IDs_once']=set(actual)==set(wanted) and len(actual)==len(wanted)
                checks[sid+'_exact_bytes_and_DNA']=all(k in actual and actual[k]['file_sha256']==hashlib.sha256(v).hexdigest() and actual[k]['records']==sequence_facts(v) for k,v in wanted.items())
                checks[sid+'_native_extension_fna']=observed['extension']=='fna' and observed['genome_dir']=='gtdbtk_input'
                manifest=outputs/(sid+'.genome_inputs.json');checks[sid+'_manifest']=manifest.is_file() and json.loads(manifest.read_text())['genomes']==len(wanted)
                summary=outputs/sid/'classify'/(sid+'.bac120.summary.tsv')
                tab=list(csv.DictReader(summary.open(),delimiter='\t'))
                checks[sid+'_summary_IDs']=len(tab)==len(wanted) and {r['user_genome'] for r in tab}==set(wanted) and all(r['classification']=='INTERFACE_OBSERVER_NOT_TAXONOMY' for r in tab)
        record={'name':name+suffix,'command':command,'exit':result.returncode,'checks':checks,'tasks':tasks,'scope':'native2.7.2 parser/selection with explicit model/DB observer'}
        runs.append(record);(base/'runs-progress.json').write_text(json.dumps(runs,indent=2)+'\n')
        assert all(checks.values()),record
    if before:
        execute('old-partial',selected=records[:1],module=before,failure='old_partial_selection')
        execute('old-no-extension',selected=[{'id':'S1','bins':[paths['A.1.fa'],paths['B.2.fa.gz']]}],module=before,failure='old_no_extension')
    execute('current');execute('current',resume=True)
    execute('conflicting-extension',extra='--extension gz')
    execute('obsolete-config-option',selected=records[:1],extra='--skip_ani_screen',failure='obsolete_option')
    execute('duplicate',selected=[{'id':'duplicate','bins':[paths['same.fa'],paths['same.fna.gz']]}],failure='duplicate')
    execute('corrupt-gzip',selected=[{'id':'corrupt','bins':[paths['A.1.fa'],paths['corrupt.fa.gz']]}],failure='gzip')
    execute('native-boundary-failure',selected=records[:1],failure='observer')
    execute('no-bin-samples',selected=[])
    assert all(sha(p)==v for p,v in original.items())
    result={'pass':True,'runs':runs,'input_genomes_sha256':original,
        'sources_sha256':{name:sha(ROOT/name) for name in ['bin/normalize_gtdb_bins.py','modules/nf-core/gtdbtk/classifywf/main.nf','tests/test_gtdb_bin_inputs.py','tests/gtdb_input_observer.py','tests/run_gtdb_inputs.py','tests/nextflow/gtdb_inputs.nf']},
        'limitations':['Actual native parser and whole _genomes_to_process method only; constructor bypassed; fake reference-ID roster',
            'No full GTDB reference package, marker search, placement, taxonomy accuracy, container or nf-test certification',
            'Taxonomy summary markers are explicit observers, not real classification output']}
    (base/'run.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir',type=Path,required=True)
    parser.add_argument('--prefix',type=Path,required=True)
    parser.add_argument('--genome',type=Path,action='append',required=True)
    parser.add_argument('--before-module',type=Path)
    args=parser.parse_args();assert len(args.genome)==2
    run(args.work_dir.resolve(),args.prefix.resolve(),[p.resolve() for p in args.genome],args.before_module.resolve() if args.before_module else None)
