#!/usr/bin/env python3
"""Complete fixed HOTSPOT normal-mode model/DB, actual workflow and cache tests.

Legacy runs use a logged ELF-only Python bootstrap so parser/cache defects can
be isolated from the separately reproduced old Torch loader failure. No source,
model, feature, taxonomy or threshold is replaced by a test double.
"""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import pickle
import shutil
import subprocess

from Bio import SeqIO

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fasta_ids(path):
    opener=gzip.open if Path(path).read_bytes()[:2]==b'\x1f\x8b' else open
    with opener(path,'rt') as stream:return {r.id:str(r.seq) for r in SeqIO.parse(stream,'fasta')}


def run(base,prefix,program,database,models,before):
    base.mkdir(parents=True)
    local_models=base/'models';shutil.copytree(models,local_models)
    fixtures=base/'fixtures';fixtures.mkdir()
    source1=program/'example_plasmids/NZ_CP050042.fasta';source2=program/'example_plasmids/NZ_CP083619.fasta'
    a=fixtures/'one.fna';a.write_bytes(source1.read_bytes())
    zipped=fixtures/'one.fna.gz';zipped.write_bytes(gzip.compress(source1.read_bytes(),mtime=0))
    b=fixtures/'two.fna';b.write_bytes(source2.read_bytes())
    records=[{'id':'S1','fasta':str(zipped)},{'id':'S.2','fasta':str(b)}]
    legacy_records=[{'id':'Legacy','fasta':str(a)}]
    labels=pickle.loads((models/'labels.dict').read_bytes());parents=pickle.loads((models/'parent.dict').read_bytes())
    tree=pickle.loads((models/'host_phylogenetic_tree.pkl').read_bytes())
    parent=local_models/'parent.dict';original=parent.read_bytes();stamp=parent.stat()
    corrupt=b'!'+original[1:];(base/'corrupt-parent.dict').write_bytes(corrupt)
    def put(data):
        parent.write_bytes(data);os.utime(parent,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
    corrupt_proof={'original_sha256':hashlib.sha256(original).hexdigest(),'corrupt_sha256':hashlib.sha256(corrupt).hexdigest(),'bytes':len(original),'mtime_ns_preserved':stamp.st_mtime_ns,'mutation':'one invalid pickle opcode; private model copy only, not original resources'}
    (base/'mutation.json').write_text(json.dumps(corrupt_proof,indent=2)+'\n')
    transport=base/'legacy-native-bin';transport.mkdir()
    shim=transport/'python3'
    shim.write_text('#!'+str(prefix/'bin/python')+'\n'
        'import importlib.util,json,os,shutil,subprocess,sys\nfrom pathlib import Path\n'
        's=importlib.util.spec_from_file_location("hotspot_abi",'+repr(str(ROOT/'bin/hotspot_runtime.py'))+');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\n'
        'program=Path(sys.argv[1]);work=Path(".legacy_compat_"+program.stem)\n'
        'environment,record=m.runtime_environment(work);environment["PYTHONDONTWRITEBYTECODE"]="1"\n'
        'environment["OMP_NUM_THREADS"]="2";environment["MKL_NUM_THREADS"]="2"\n'
        'command=m.command(program,sys.argv[2:],record["private_elf_compatibility"])\n'
        'try:\n r=subprocess.run(command,env=environment);record.update(command=command,exit_code=r.returncode,scope="native original source with ELF-only bootstrap; not a classifier observer")\n'
        'finally:\n Path("legacy_abi_"+program.stem+".json").write_text(json.dumps(record,indent=2));shutil.rmtree(work,ignore_errors=True)\n'
        'raise SystemExit(r.returncode)\n')
    shim.chmod(0o755)
    runs=[]
    def execute(name,chosen=records,legacy=False,resume=False,disabled=False,failure=False,conda=False):
        folder=base/name;folder.mkdir(exist_ok=resume)
        workflow=ROOT/'tests/nextflow/hotspot.nf'
        if legacy:
            workflow=folder/'legacy.nf'
            if not resume:workflow.write_text("nextflow.enable.dsl=2\ninclude { LINK_HOTSPOT } from "+repr(str(before.with_suffix('')))+"\nworkflow { LINK_HOTSPOT(Channel.value(tuple([id:'Legacy'],file(params.records[0].fasta,checkIfExists:true)))) ; LINK_HOTSPOT.out.links.view { value -> 'HOTSPOT_LINK='+value } }\n")
        config=folder/'nextflow.config'
        if not resume:
            config.write_text("process { executor='local'; cpus=2; memory='3 GB'; maxForks=2; errorStrategy='terminate'; maxRetries=0 }\n"
                "docker.enabled=false\nsingularity.enabled=false\n"
                'conda { enabled='+str(conda).lower()+';useMicromamba='+str(conda).lower()+";cacheDir="+repr(str(base/'conda-cache'))+";createOptions='--offline' }\n")
            params={'records':chosen,'host_plasmid_linking':True,'host_linking_methods':[],
                    'host_linking_optional_methods':[] if disabled else ['hotspot'],
                    'hotspot_home':str(program),'hotspot_db':str(database),'hotspot_models':str(local_models),'outdir':str(folder/'out')}
            (folder/'params.json').write_text(json.dumps(params,indent=2))
        suffix=('-corrupt-resume' if failure else '-resume') if resume else ''
        trace=folder/('trace'+suffix+'.tsv');key='hotspot_'+hashlib.sha256(str(folder).encode()).hexdigest()[:12]
        cmd=[str(ROOT/'results/tool-audit/runtime/bin/nextflow'),'-C',str(config),'run',str(workflow),'-params-file',str(folder/'params.json'),'-work-dir',str(folder/'work'),'-with-trace',str(trace),'-ansi-log','false']
        cmd+=['-resume',key] if resume else ['-name',key]
        environment={**os.environ,'PATH':(str(transport)+':' if legacy else '')+str(prefix/'bin')+':'+os.environ['PATH'],
                     'PYTHONDONTWRITEBYTECODE':'1','MAMBA_ROOT_PREFIX':str(ROOT/'results/tool-audit/runtime/mamba-root')}
        result=subprocess.run(cmd,env=environment,capture_output=True,text=True)
        (folder/('stdout'+suffix+'.log')).write_text(result.stdout);(folder/('stderr'+suffix+'.log')).write_text(result.stderr)
        tasks=list(csv.DictReader(trace.open(),delimiter='\t')) if trace.exists() else []
        record={'scenario':name+suffix,'command':cmd,'exit_code':result.returncode,'trace':tasks,'mutated_model':failure}
        runs.append(record);(base/'runs-progress.json').write_text(json.dumps(runs,indent=2)+'\n')
        checks={}
        if failure and not legacy:
            errors='\n'.join(p.read_text() for p in (folder/'work').rglob('.command.err'))
            checks={'changed_resource_invalidates_cache':result.returncode!=0 and any(t['status']=='FAILED' for t in tasks) and not any(t['status']=='CACHED' for t in tasks),
                    'native_pickle_error':'UnpicklingError' in errors,'no_successful_link_emit':'HOTSPOT_LINK=' not in result.stdout}
        elif disabled or not chosen:
            checks={'no_analysis_tasks':result.returncode==0 and not tasks}
        else:
            checks['success']=result.returncode==0
            checks['all_tasks_correct']=len(tasks)==len(chosen) and all(t['status']==('CACHED' if resume else 'COMPLETED') for t in tasks)
            for row in chosen:
                sid=row['id'];out=folder/'out/07_host_prediction/linking/hotspot'
                raw=out/(sid+'.host_lineage.tsv');links=out/(sid+'.hotspot_links.tsv')
                if not raw.exists() or not links.exists():checks[sid+'_outputs_present']=False;continue
                with raw.open(newline='') as stream:lineage=list(csv.DictReader(stream,delimiter='\t'))
                ids=fasta_ids(row['fasta']);expected={}
                for taxon in lineage:
                    cid=taxon['Contig'];assert cid in ids
                    levels=[taxon[level] for level in ['Phylum','Class','Order','Family','Genus','Species']]
                    nonmissing=[v for v in levels if v not in ['','-']]
                    assert nonmissing
                    for depth,value in enumerate(levels):
                        if value=='-':continue
                        # Upstream may inherit the sole child of the previous
                        # taxon even when it has no classifier output slot.
                        if value not in labels[depth]:
                            assert depth > 0
                            children=tree.children(levels[depth-1])
                            assert len(children)==1 and children[0].identifier==value
                        if depth:assert parents[value]==levels[depth-1]
                    expected[cid]=nonmissing[-1]
                checks[sid+'_native_lineage_ids']=set(expected)==set(ids)
                if legacy:
                    actual={line.split(b'\t')[0].decode():line.split(b'\t')[1] for line in links.read_bytes().split(b'\n')[1:] if line}
                    checks[sid+'_original_CR_taxon_bug']=set(actual)==set(expected) and any(actual[k]!=v.encode() and b'\r' in actual[k] for k,v in expected.items())
                    if failure:checks['legacy_ignores_corrupt_model']=all(t['status']=='CACHED' for t in tasks)
                else:
                    with links.open(newline='') as stream:converted=list(csv.DictReader(stream,delimiter='\t'))
                    checks[sid+'_exact_host_and_sample']=len(converted)==len(expected) and {v['plasmid_id']:v['host_id'] for v in converted}==expected and all(v['sample_id']==sid and v['evidence_type']=='hotspot' and v['score']=='' for v in converted)
                    checks[sid+'_no_CR_or_placeholder']=b'\r' not in links.read_bytes() and all(v['host_id'] not in ['','-'] for v in converted)
                    metadata=json.loads((out/(sid+'.hotspot_runtime.json')).read_text())
                    conversion=json.loads((out/(sid+'.hotspot_conversion.json')).read_text())
                    checks[sid+'_source_and_normal_method']=metadata['source_commit']=='0e3e3013a6a29fbdadc8e58180c9eb259877ce99' and len(metadata['steps'])==2 and all(v['exit_code']==0 for v in metadata['steps']) and 'no MC-dropout' in metadata['method']
                    checks[sid+'_input_and_attribution']=metadata['input_sha256']==sha(row['fasta']) and not conversion['source_ids_not_in_lineage'] and conversion['sample_id']==sid
                    checks[sid+'_full_resources']=sum(v['bytes'] for v in metadata['models'].values())==1911643940 and sum(v['bytes'] for v in metadata['database'].values())==273686908
                    if conda:checks['fresh_locked_conda_used']=str(base/'conda-cache') in metadata['python_executable']
        record['checks']=checks;record['pass']=all(checks.values())
        (base/'runs-progress.json').write_text(json.dumps(runs,indent=2)+'\n')
        print(record['scenario'],record['pass'],checks,flush=True)
        assert record['pass'],(record,result.stdout[-2500:],result.stderr[-2500:])
    try:
        execute('legacy',legacy_records,legacy=True)
        put(corrupt);execute('legacy',legacy_records,legacy=True,resume=True,failure=True)
        put(original)
        execute('current')
        execute('current',resume=True)
        put(corrupt);execute('current',resume=True,failure=True)
        put(original)
        execute('disabled',disabled=True)
        execute('no-input',chosen=[])
        execute('locked-conda',chosen=records[:1],conda=True)
    finally:put(original)
    sources=['modules/linking/hotspot.nf','subworkflows/host_linking.nf','bin/convert_hotspot_lineage.py','bin/hotspot_runtime.py','envs/hotspot.yml','envs/hotspot-linux-64.lock','tests/nextflow/hotspot.nf','tests/run_hotspot_native.py']
    payload={'pass':True,'runs':runs,'source_sha256':{f:sha(ROOT/f) for f in sources},
             'inputs':{str(p):sha(p) for p in [source1,source2,before]},
             'limitations':['Complete fixed official models/DB and real original normal-mode programs; ELF bootstrap alters private GNU_STACK metadata only, never source/weights/thresholds.',
                            'Legacy wrapper requires a logged ELF-only Python transport to isolate its actual CR/parser and resource-cache defects; no classifier observer.',
                            'Model corruption is a private copied input boundary, not a scientific method or retrained model; source originals restored/unchanged.',
                            'Taxonomy-label/hierarchy, sequence/sample attribution and interface parity only, not biological host-range/sensitivity/accuracy validation.',
                            'Official examples may overlap training; no independent biological replicates claimed. Current native and fixed-lock Conda only; no image/AWS/full platform/nf-test claim.']}
    (base/'run.json').write_text(json.dumps(payload,indent=2)+'\n');print('HOTSPOT native workflow/cache checks passed')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['output','prefix','program','database','models','before']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();run(args.output.resolve(),args.prefix.resolve(),args.program.resolve(),args.database.resolve(),args.models.resolve(),args.before.resolve())
