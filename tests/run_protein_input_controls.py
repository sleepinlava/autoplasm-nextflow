#!/usr/bin/env python3
"""Native failure controls; original wrapper swallowing error is not a pass."""
import argparse
import csv
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def run(base, prefix, models, proteins, genome, before):
    base.mkdir(parents=True)
    bad=base/'malformed_topology.txt';bad.write_text('not-a-valid-topology-entry\n')
    env={**os.environ,'PATH':str(prefix/'bin')+':'+os.environ['PATH']}
    runs=[]
    for name,old in [('original-swallowed-failure',True),('fixed-propagates-failure',False)]:
        folder=base/name;folder.mkdir()
        workflow=ROOT/'tests/nextflow/macsy_inputs.nf'
        if old:
            workflow=folder/'original.nf'
            workflow.write_text((ROOT/'tests/nextflow/macsy_inputs.nf').read_text()
                .replace("'../../modules/nf-core/macsyfinder/search/main'",repr(str(before.with_suffix(''))))
                .replace(',file(params.topology,checkIfExists:true)', ''))
        config=folder/'nextflow.config'
        args='--db-type gembase --replicon-topology linear'
        if old:args+=' --topology-file '+str(bad)
        config.write_text("process { executor='local'; cpus=1; memory='1 GB'; errorStrategy='terminate'; maxRetries=0; withName:'CONJSCAN' { ext.args="+repr(args)+" } }\n"
                          "conda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\n")
        params={'proteins':str(proteins),'models':str(models),'topology':str(bad)}
        (folder/'params.json').write_text(json.dumps(params))
        trace=folder/'trace.tsv'
        cmd=[str(ROOT/'results/tool-audit/runtime/bin/nextflow'),'-C',str(config),'run',str(workflow),'-params-file',str(folder/'params.json'),'-work-dir',str(folder/'work'),'-with-trace',str(trace),'-ansi-log','false']
        result=subprocess.run(cmd,env=env,capture_output=True,text=True)
        (folder/'stdout.log').write_text(result.stdout);(folder/'stderr.log').write_text(result.stderr)
        tasks=list(csv.DictReader(trace.open(),delimiter='\t')) if trace.exists() else []
        errors='\n'.join(p.read_text() for p in (folder/'work').rglob('.command.err'))
        checks={'one_native_task':len(tasks)==1,'native_topology_error':'ValueError: not enough values to unpack' in errors}
        if old:checks['old_error_hidden']=result.returncode==0 and tasks[0]['status']=='COMPLETED'
        else:checks['current_failure_propagates']=result.returncode!=0 and tasks[0]['status']=='FAILED'
        record={'scenario':name,'command':cmd,'exit_code':result.returncode,'trace':tasks,'checks':checks}
        runs.append(record);(base/'runs-progress.json').write_text(json.dumps(runs,indent=2)+'\n');assert all(checks.values()),record
    # Correct models isolate the sequence-type bug from the separate obsolete
    # CONJ package/model argument. This real plasmid exceeds HMMER's 100K
    # protein limit when its nucleotide sequence is passed as one "protein".
    for name,args in [('original-dna',['--sequence-db',str(genome),'--models','CONJScan/Plasmids','all']),
                      ('original-model-name',['--sequence-db',str(proteins),'--models','CONJ'])]:
        folder=base/name;folder.mkdir()
        cmd=['macsyfinder',*args,'--models-dir',str(models),'--db-type','ordered_replicon','--worker','1','--out-dir',str(folder/'output')]
        # MacSyLib's HMMER error handler kills its entire process group.
        # Isolate the direct negative control so the harness survives to
        # preserve the real exit code and diagnostic; no tool error is caught
        # and converted into a biological empty result.
        result=subprocess.run(cmd,env=env,capture_output=True,text=True,start_new_session=True)
        (folder/'stdout.log').write_text(result.stdout);(folder/'stderr.log').write_text(result.stderr)
        record={'scenario':name,'command':cmd,'exit_code':result.returncode}
        if name=='original-dna':
            diagnostic='\n'.join(p.read_text() for p in (folder/'output/hmmer_results').glob('*.search_hmm.err'))
            assert result.returncode!=0 and 'Target sequence length > 100K' in diagnostic
            assert not (folder/'output/all_systems.tsv').exists()
            record['checks']={'native_DNA_protein_limit_failure_reproduced':True}
        else:
            assert result.returncode!=0 and 'CONJ' in result.stderr
            record['checks']={'obsolete_model_name_rejected':True}
        runs.append(record)
    (base/'run.json').write_text(json.dumps({'pass':True,'runs':runs,
        'limitations':['Malformed topology is an explicit error-propagation boundary, not a biological negative.',
                       'Original DNA reaches HMMER protein length failure; no biological specificity claim.']},indent=2)+'\n')
    print('4 native controls passed (2 Nextflow wrapper tasks,2 direct CLI controls)')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['output','prefix','models','proteins','genome','before']:parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args()
    run(args.output.resolve(),args.prefix.resolve(),args.models.resolve(),args.proteins.resolve(),args.genome.resolve(),args.before.resolve())
