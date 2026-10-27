#!/usr/bin/env python3
"""Native fixed2.4.1 default self training, output states and checkpoint emits.

The no-bin boundary uses an explicit minimum size greater than the complete
official input. It is not a model sensitivity/specificity benchmark. Stub and
native failures are kept separate from successful inference.
"""
from module_harness import render_module_harness, run_session_uuid
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
from Bio import SeqIO
import gzip

ROOT=Path(__file__).resolve().parents[1]


def dna(path):
    opener=gzip.open if str(path).endswith('.gz') else open
    with opener(path,'rt') as stream:return {s.id:str(s.seq) for s in SeqIO.parse(stream,'fasta')}


def run(base,prefix,fixture,before):
    base.mkdir(parents=True)
    source=dna(fixture/'input.fasta');assert len(source)==40 and sum(map(len,source.values()))==800000
    env={**os.environ,'PATH':str(prefix/'bin')+':'+os.environ['PATH'],'OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','MKL_NUM_THREADS':'2'}
    runs=[]
    def execute(name,extra='',original=False,stub=False,resume=False):
        folder=base/name;folder.mkdir(exist_ok=resume)
        config=folder/'nextflow.config'
        if not resume:
            config.write_text("process { executor='local'; cpus=2; memory='2 GB'; errorStrategy='terminate'; maxRetries=0; publishDir=[path:"+repr(str(folder/'out'))+",mode:'copy']; withName:'SEMIBIN|SEMIBIN_RESOURCE_PROBE' { ext.args2="+repr('--random-seed 0 '+extra)+" } }\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\n")
            (folder/'params.json').write_text(json.dumps({'fasta':str(fixture/'input.fasta'),'bam':str(fixture/'input.sorted.bam'),'original':original}))
        workflow=ROOT/'tests/nextflow/semibin_states.nf'
        if original:
            workflow=folder/'original.nf'
            historical_template=folder/'historical-template.nf'
            historical_template.write_bytes(subprocess.check_output(['git','show','HEAD:tests/nextflow/semibin_states.nf'],cwd=ROOT))
            workflow.write_text(render_module_harness(historical_template, '../../modules/nf-core/semibin/singleeasybin/main', before, 'semibin_output_state.py'))
        suffix='-resume' if resume else '';trace=folder/('trace'+suffix+'.tsv')
        name_key='semibin_'+hashlib.sha256(str(folder).encode()).hexdigest()[:12]
        cmd=[str(ROOT/'results/tool-audit/runtime/bin/nextflow'),'-C',str(config),'run',str(workflow),'-params-file',str(folder/'params.json'),'-work-dir',str(folder/'work'),'-with-trace',str(trace),'-ansi-log','false']
        cmd+=['-resume',run_session_uuid(name_key,folder)] if resume else ['-name',name_key]
        if stub:cmd+=['-stub-run']
        result=subprocess.run(cmd,cwd=folder,env=env,capture_output=True,text=True)
        (folder/('stdout'+suffix+'.log')).write_text(result.stdout);(folder/('stderr'+suffix+'.log')).write_text(result.stderr)
        tasks=list(csv.DictReader(trace.open(),delimiter='\t')) if trace.exists() else []
        record={'scenario':name+suffix,'command':cmd,'exit_code':result.returncode,'trace':tasks}
        runs.append(record);(base/'runs-progress.json').write_text(json.dumps(runs,indent=2)+'\n')
        if name!='native-failure':
            consumer=[t for t in tasks if t['name'].startswith('SEMIBIN (')]
            assert len(consumer)==1,record
            if not original:
                probes=[t for t in tasks if t['name'].startswith('SEMIBIN_RESOURCE_PROBE')]
                assert len(probes)==1 and probes[0]['status']=='COMPLETED',record
            tasks=consumer
        if name=='native-failure':
            assert len(tasks)==1 and tasks[0]['name'].startswith('SEMIBIN_RESOURCE_PROBE'),record
            checks={'native_failure_propagates':result.returncode!=0 and tasks[0]['status']=='FAILED',
                    'native_parser_diagnostic':'unrecognized arguments' in result.stdout+result.stderr,
                    'no_fake_state':not (folder/'out/sample/binning_status.json').exists()}
            record['checks']=checks;assert all(checks.values()),record;return
        assert result.returncode==0 and tasks[0]['status']==('CACHED' if resume else 'COMPLETED'),record
        output=folder/'out/sample';bins=list((output/'output_bins').glob('*.fa.gz'))
        checks={'sample_bin_emission':('BIN_EMIT=sample' in result.stdout)==bool(bins)}
        if original:
            # The old .h5 glob omits the real .pt checkpoint from its channel.
            actual=list((folder/'work').rglob('sample/model.pt'))
            checks.update(real_checkpoint_exists=len(actual)==1,old_checkpoint_emit_missing='MODEL_EMIT=' not in result.stdout and not (output/'model.pt').exists())
        else:
            state=json.loads((output/'binning_status.json').read_text())
            if stub:
                checks.update(stub_explicit=state['state']=='stub_not_validated' and state['bin_count'] is None,
                              no_manufactured_bins=not bins,no_manufactured_checkpoint=not (output/'model.pt').exists())
            else:
                empty=name=='no-bins'
                checks.update(state_matches=state['state']==('no_bins' if empty else 'bins_ready') and state['bin_count']==len(bins),
                              correct_empty_boundary=(not bins) if empty else bool(bins),
                              checkpoint_emitted=(output/'model.pt').is_file() and 'MODEL_EMIT=sample' in result.stdout)
                if not empty:
                    seen=set();metrics={v['filename']:v for v in state['bins']}
                    for path in bins:
                        contents=dna(path);assert contents and not (seen&contents.keys())
                        assert all(k in source and value==source[k] for k,value in contents.items())
                        seen.update(contents);entry=metrics[path.name]
                        lengths=sorted(map(len,contents.values()),reverse=True);total=sum(lengths);cumulative=0
                        for rank,length in enumerate(lengths,1):
                            cumulative+=length
                            if cumulative>=total/2:break
                        assert (entry['nbps'],entry['nr_contigs'],entry['N50'],entry['L50'])==(total,len(contents),length,rank)
                    checks['independent_bin_DNA_membership_metrics']=True
                # Use the fixed native program's safe model loader; verify the
                # newly exposed checkpoint is readable and finite, not just named .pt.
                code='import sys,torch; from SemiBin.semi_supervised_model import model_load; m=model_load(sys.argv[1],torch.device("cpu")); assert all(torch.isfinite(x).all() for x in m.parameters()); print(type(m).__name__)'
                loaded=subprocess.run([str(prefix/'bin/python'),'-c',code,str(output/'model.pt')],env=env,capture_output=True,text=True)
                (folder/('checkpoint-load'+suffix+'.log')).write_text(loaded.stdout+loaded.stderr)
                checks['checkpoint_native_loads_finite']=loaded.returncode==0
        record['checks']=checks
        assert all(checks.values()),record
        print(name+suffix,checks,flush=True)
    execute('original-positive',original=True)
    execute('positive')
    execute('positive',resume=True)
    execute('no-bins','--minfasta-kbs 1000')
    execute('stub',stub=True)
    execute('native-failure','--not-a-real-option')
    files=['lib/semibin_runtime.nf','bin/semibin_runtime_resources.py','bin/semibin_output_state.py','modules/nf-core/semibin/singleeasybin/main.nf','tests/test_semibin_output_state.py','tests/run_semibin_states.py','tests/nextflow/semibin_states.nf']
    payload={'pass':True,'runs':runs,'source_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files},
             'fixture_sha256':{f:hashlib.sha256((fixture/f).read_bytes()).hexdigest() for f in ['input.fasta','input.sorted.bam']},
             'limitations':['Native CPU only; exact official fixture identity and DNA/metrics verified, not biological clustering accuracy/MAG quality.',
                            'No-bin uses declared size-filter boundary greater than total input; default self-supervised 15epochs retained; random seed0 fixed.',
                            'Original legitimate-zero failure is a separate retained original module run; original missing model emit and current .pt model load are checked here.',
                            'Resource probes run before cache lookup; unknown-argument control fails native parser in the probe before inference. Stub performs no inference; model/status assertions replace outdated empty-model/positive-stub snapshots. Vendored nf-test/GPU/images/full platforms not certified.']}
    (base/'run.json').write_text(json.dumps(payload,indent=2)+'\n')
    print('native SemiBin states passed',len(runs),'scenarios,',sum(len(r['trace']) for r in runs),'trace entries')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['output','prefix','fixture','before']:parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();run(args.output.resolve(),args.prefix.resolve(),args.fixture.resolve(),args.before.resolve())
