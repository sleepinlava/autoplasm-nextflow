#!/usr/bin/env python3
"""Actual CROSS_SAMPLE, native R and FastSpar; explicit count/cohort controls.

No assemblies, classifiers or wet-lab association accuracy is certified here.
"""
import argparse,csv,hashlib,json,math,os,random,re,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def table(path):
    with path.open() as f:return list(csv.DictReader(f,delimiter='\t'))


def generate(folder,kind):
    folder.mkdir();ids=['001','1','NA']+[f'S{i}' for i in range(3,20)];rng=random.Random(1301438)
    if kind in ['empty']:values=[]
    elif kind in ['single']:values=[[5+i for i in range(20)]]
    elif kind=='one-nonzero':values=[[10+j if i==0 else 0 for i in range(20)] for j in range(4)]
    elif kind=='all-zero':values=[[0]*20 for _ in range(4)]
    elif kind=='low-features':values=[[5+i+j for i in range(20)] for j in range(3)]
    elif kind=='filtered-zero':values=[[10 if i==j else 0 for i in range(20)] for j in range(20)]
    elif kind=='new-zero':values=[[5+j if i<4 else 0 for i in range(20)] for j in range(4)]+[[10 if i==j else 0 for i in range(20)] for j in range(4,20)]
    else:values=[[rng.randint(50,500) for i in range(20)] for j in range(8)]
    features=[f'F{i}' for i in range(len(values))];meta='sample_id\tgroup\n'+''.join(sid+'\t'+('A' if i<10 else 'B')+'\n' for i,sid in enumerate(ids));(folder/'samples.tsv').write_text(meta)
    for role,featurecol in [('contigs','contig_id'),('plasmids','plasmid_id')]:
        text=featurecol+'\tsample_id\tcoverage\traw_count\n'
        for j,fid in enumerate(features):
            for i,sid in enumerate(ids):
                if kind=='missing-sample' and sid=='NA':continue
                text+=f'{fid}\t{sid}\t{values[j][i]/10}\t{values[j][i]}\n'
        (folder/(role+'.tsv')).write_text(text)
    states='sample_id\treference_features\tplasmid_features\teligible_read_alignments\tplasmid_read_alignments\tquantification_status\n'
    for i,sid in enumerate(ids):
        total=sum(row[i] for row in values);status='empty_catalogue' if not features else 'measured_zero' if not total else 'measured';declared=999999 if kind=='bad-state' and i==0 else total;states+=f'{sid}\t{len(features)}\t{len(features)}\t{declared}\t{total}\t{status}\n'
        sample=folder/sid;sample.mkdir();rng_dna=random.Random(1438);dna=[''.join(rng_dna.choices('ACGT',k=1200)) for _ in features]
        (sample/'plasmids.fasta').write_text(''.join('>'+fid+'\n'+seq+'\n' for fid,seq in zip(features,dna)))
        (sample/'consensus.tsv').write_text('sample_id\tcontig_id\tplasmid_call\tsupporting_tools\n'+''.join(sid+'\t'+fid+'\tplasmid\tcontrolled_fixture\n' for fid in features))
        (sample/'structure.tsv').write_text('sample_id\tplasmid_id\tis_circular\n'+''.join(sid+'\t'+fid+'\tfalse\n' for fid in features))
    (folder/'states.tsv').write_text(states)
    return ids,features,values


def before_harness(base,before):
    # Freeze old CROSS_SAMPLE and all changed process interfaces. Other includes
    # resolve to current unchanged dependencies; R executables use frozen PATH.
    old=(before/'subworkflows/cross_sample.nf').read_text()
    def target(match):
        name=match.group(1);resolved=(ROOT/'subworkflows'/name).resolve()
        if name in ['../modules/cross_sample/'+n for n in ['network_prepare','diversity','differential','deseq2']]:resolved=before/'modules/cross_sample'/Path(name).name
        return "from '"+str(resolved)+"'"
    old=re.sub(r"from '([^']+)'",target,old);(base/'old-cross.nf').write_text(old)
    text=(ROOT/'tests/nextflow/statistics_eligibility.nf').read_text().replace("'../../subworkflows/cross_sample'",repr(str(base/'old-cross'))).replace("'../../lib/report_events'",repr(str(ROOT/'lib/report_events'))).replace('file("${root}/plasmids.tsv",checkIfExists:true)),states,Channel.empty()','file("${root}/plasmids.tsv",checkIfExists:true)),Channel.empty()')
    (base/'probe.nf').write_text(text);return base/'probe.nf'


def square(path,features,correlation=False):
    with path.open() as f:r=csv.DictReader(f,delimiter='\t');fields=r.fieldnames;rows=list(r)
    assert set(fields[1:])==set(features) and len(rows)==len(features);first=fields[0];assert {r[first] for r in rows}==set(features)
    values={r[first]:{fid:float(r[fid]) for fid in features} for r in rows}
    for fid in features:
        for other in features:
            v=values[fid][other];assert math.isfinite(v);assert math.isclose(v,values[other][fid],abs_tol=1e-5)
            if correlation:assert -1.000001<=v<=1.000001
        if correlation:assert math.isclose(values[fid][fid],1,abs_tol=1e-6)
    return values


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work-dir',type=Path,required=True);p.add_argument('--fastspar-prefix',type=Path,required=True);p.add_argument('--before-dir',type=Path,required=True);p.add_argument('--python-prefix',type=Path,required=True);a=p.parse_args();base=a.work_dir.resolve();base.mkdir(parents=True,exist_ok=False);before=a.before_dir.resolve();fastspar=a.fastspar_prefix.resolve()/'bin';python_bin=a.python_prefix.resolve()/'bin';python_version=subprocess.run([str(python_bin/'python3'),'--version'],capture_output=True,text=True,check=True).stdout.strip();assert python_version.startswith('Python 3.12.')
    sources=['bin/collect_shared_abundance.py','main.nf','subworkflows/cross_sample.nf','modules/cross_sample/statistics_inputs.nf','modules/cross_sample/network_prepare.nf','modules/cross_sample/fastspar.nf','modules/cross_sample/diversity.nf','bin/validate_statistics_inputs.py','bin/statistics_input_contract.R','bin/diversity.R','bin/network_prepare.R','tests/run_statistics_eligibility.py','tests/nextflow/statistics_eligibility.nf'];hashes={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sources};runs=[]
    cases=['before-filtered-zero','positive','single','empty','all-zero','one-nonzero','low-features','filtered-zero','new-zero','missing-sample','bad-state','missing-state-channel','duplicate-table-channel']
    for name in cases:
        old=name.startswith('before-');kind='filtered-zero' if old else name;d=base/name;d.mkdir();fixture=d/'fixtures';ids,features,values=generate(fixture,kind);fixture_hash={str(q.relative_to(fixture)):hashlib.sha256(q.read_bytes()).hexdigest() for q in fixture.rglob('*') if q.is_file()};(d/'inputs-before.json').write_text(json.dumps(fixture_hash,indent=2)+'\n')
        harness=before_harness(d,before) if old else ROOT/'tests/nextflow/statistics_eligibility.nf';config=d/'native.config';config.write_text("process.executor='local'\nprocess.cpus=1\nprocess.memory='1 GB'\nprocess.maxForks=1\nconda.enabled=false\ndocker.enabled=false\nsingularity.enabled=false\ntrace.fields='task_id,hash,name,status,exit,workdir'\n")
        params={'fixture_dir':str(fixture),'sample_ids':ids,'samplesheet':str(fixture/'samples.tsv'),'outdir':str(d/'out'),'publish_dir_mode':'copy','platform':'illumina','run_diversity':not old,'min_diversity_samples':3,'run_differential_internal':False,'run_differential_deseq2':False,'run_network':True,'network_min_samples':20,'project_name':'controlled_statistics_not_biological_benchmark','omit_state':name=='missing-state-channel','duplicate_contig_table':name=='duplicate-table-channel'};(d/'params.json').write_text(json.dumps(params))
        cmd=[shutil.which('nextflow') or 'nextflow','-C',str(config),'run',str(harness),'-params-file',str(d/'params.json'),'-work-dir',str(d/'work'),'-with-trace',str(d/'trace.tsv'),'-ansi-log','false'];env=os.environ.copy();env['PATH']=str(fastspar)+':'+str(python_bin)+':'+str(before/'bin' if old else ROOT/'bin')+':'+env['PATH'];r=subprocess.run(cmd,text=True,capture_output=True,env=env);(d/'console.log').write_text(r.stdout+r.stderr);tasks=table(d/'trace.tsv') if (d/'trace.tsv').exists() else [];names=[t['name'].split(' (')[0].split(':')[-1] for t in tasks];negative=name in ['missing-sample','bad-state','missing-state-channel','duplicate-table-channel'];expected_failure=old or negative
        assert (r.returncode!=0)==expected_failure,(name,r.stdout+r.stderr)
        if expected_failure:
            if old:assert 'FASTSPAR' in names and 'SparCC algorithm requires at least 4' in ''.join(q.read_text() for q in (d/'work').rglob('.command.err'))
            else:assert not set(names)&{'DIVERSITY','NETWORK_PREPARE','FASTSPAR','REPORT'}
            assert not (d/'out/report/report_data.json').exists()
        else:
            assert all(t['status']=='COMPLETED' and t['exit']=='0' for t in tasks);status=json.load(open(d/'out/12_network/network_status.json'));eligible=name=='positive';assert status['eligible']==eligible;assert names.count('FASTSPAR')==int(eligible)
            alpha=table(d/'out/11_diversity/diversity_metrics.tsv');assert len(alpha)==80 and {r['sample_id'] for r in alpha}==set(ids);assert all(math.isfinite(float(r['value'])) for r in alpha)
            if name in ['single','empty','all-zero']:assert all(float(row['value'])==0 for row in alpha if row['metric']!='richness')
            if name in ['empty','all-zero']:assert all(float(row['value'])==0 for row in alpha)
            if name=='single':assert all(float(row['value'])==1 for row in alpha if row['metric']=='richness')
            if name=='one-nonzero':assert status['included_sample_ids']==[ids[0]] and status['reason']=='insufficient_samples'
            if name=='new-zero':assert status['reason']=='insufficient_samples' and len(status['included_sample_ids'])==4 and len(status['excluded_zero_after_prevalence'])==16
            report=json.load(open(d/'out/report/report_data.json'));assert {r['sample_id'] for r in report['samples']}==set(ids)
            if eligible:
                corr=square(d/'out/12_network/correlation.tsv',features,True);cov=square(d/'out/12_network/covariance.tsv',features)
                direct=d/'direct';direct.mkdir();matrix=d/'out/12_network/fastspar_eligible.tsv';dcmd=[str(fastspar/'fastspar'),'--otu_table',str(matrix),'--correlation',str(direct/'correlation.tsv'),'--covariance',str(direct/'covariance.tsv'),'--threads','1'];direct_result=subprocess.run(dcmd,text=True,capture_output=True,env=env);(direct/'console.log').write_text(direct_result.stdout+direct_result.stderr);assert direct_result.returncode==0;assert square(direct/'correlation.tsv',features,True)==corr and square(direct/'covariance.tsv',features)==cov
        assert fixture_hash=={str(q.relative_to(fixture)):hashlib.sha256(q.read_bytes()).hexdigest() for q in fixture.rglob('*') if q.is_file()};assert hashes=={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sources};runs.append({'case':name,'command':cmd,'exit':r.returncode,'tasks':tasks,'expected_failure':expected_failure});(base/'run.json').write_text(json.dumps({'pass':len(runs)==len(cases),'expected_cases':len(cases),'validator_python':python_version,'runs':runs,'source_sha256':hashes,'limitations':['explicit synthetic full-cohort integer count/reference-state and detection fixtures; no real mapping/classifier/biological network accuracy','native R/FastSpar1.0.0 positive output identities/numeric invariants and directCLI parity, not independent ecological truth or significance estimation','frozen before workflow/NETWORK_PREPARE/R used only controlled empty-after-filter counterexample','no image/remote executor/nf-test framework/full model/platform certification']},indent=2)+'\n');print('PASS',name,len(tasks),'trace tasks',flush=True)


if __name__=='__main__':main()
