#!/usr/bin/env python3
"""Native Bowtie2 sample association regression: actual workflows, controlled sequence truth.

Requires Bowtie2 2.5.4/SAMtools1.21/pigz2.8 and CoverM0.7.0/SAMtools1.24
prefixes. This is not a complete platform or biological accuracy benchmark.
"""
from pathlib import Path
import argparse,csv,gzip,hashlib,json,math,os,random,re,shutil,subprocess,tempfile


def coverage_abundance(root,p,data,bow,cov,nextflow):
    p.mkdir(parents=True,exist_ok=True)
    (p/'probe.nf').write_text(f'''nextflow.enable.dsl = 2
    include {{ CONTIG_COVERAGE }} from '{root}/subworkflows/contig_coverage'
    include {{ PLASMID_ABUNDANCE }} from '{root}/subworkflows/plasmid_abundance'
    workflow {{
        refs = Channel.fromList(['A','B'].collect {{ id -> tuple([id:id,single_end:false],file('{data}/'+id+'.fa')) }})
        reads = Channel.fromList(['A','B'].collect {{ id -> tuple([id:id,single_end:false],file('{data}/'+id+'_R1.fq'),file('{data}/'+id+'_R2.fq')) }})
        CONTIG_COVERAGE(refs,reads,Channel.empty(),'map-ont')
        PLASMID_ABUNDANCE(refs,reads,Channel.empty(),'map-ont',false)
        CONTIG_COVERAGE.out.table.view {{ meta,table -> 'COVERAGE_TABLE\\t'+meta.id+'\\t'+table }}
        PLASMID_ABUNDANCE.out.short_abundance.view {{ meta,table -> 'ABUNDANCE_TABLE\\t'+meta.id+'\\t'+table }}
    }}
    ''')
    (p/'config').write_text(f'''params.outdir = '{p}/out'
    params.publish_dir_mode = 'copy'
    includeConfig '{root}/conf/nfcore_upstream.config'
    process.executor = 'local'
    process.cpus = 1
    process.memory = '1 GB'
    executor.queueSize = 6
    process {{
        withName: '.*BOWTIE2_BUILD_.*' {{
            beforeScript = {{ meta.id == 'A' ? 'sleep 6' : 'sleep 0' }}
        }}
        withName: '.*SAMTOOLS_MERGE' {{
            beforeScript = 'export PATH="{cov}:$PATH"'
        }}
        withName: '.*COVERM_.*' {{
            beforeScript = 'export PATH="{cov}:$PATH"'
        }}
    }}
    conda.enabled = false
    docker.enabled = false
    singularity.enabled = false
    ''')
    env=os.environ.copy();env['PATH']=str(bow)+':'+env['PATH'];command=[nextflow,'-C',str(p/'config'),'run',str(p/'probe.nf'),'-work-dir',str(p/'work'),'-with-trace',str(p/'trace.tsv'),'-ansi-log','false'];r=subprocess.run(command,env=env,text=True,capture_output=True);(p/'stdout.log').write_text(r.stdout);(p/'stderr.log').write_text(r.stderr)
    checks={'workflow_success':r.returncode==0};observations=[]
    if r.returncode==0:
     for sid in ['A','B']:
      for kind,bam,table in [('coverage',p/f'out/02_assembly/coverage/samtools/{sid}.contig_alignment.bam',p/f'out/02_assembly/coverage/coverm/{sid}.contig_coverm.tsv'),('abundance',p/f'out/10_abundance/samtools/{sid}.bam',p/f'out/10_abundance/coverm/{sid}.coverm.tsv')]:
       header=subprocess.run([str(bow/'samtools'),'view','-H',str(bam)],capture_output=True,text=True,check=True).stdout;(p/f'{sid}.{kind}.header.sam').write_text(header)
       sq=[dict(x.split(':',1) for x in line.split('\t')[1:]) for line in header.splitlines() if line.startswith('@SQ\t')]
       mapped=int(subprocess.run([str(bow/'samtools'),'view','-c','-F','4',str(bam)],capture_output=True,text=True,check=True).stdout)
       sam_records=subprocess.run([str(bow/'samtools'),'view',str(bam)],capture_output=True,text=True,check=True).stdout
       qnames={line.split('\t')[0] for line in sam_records.splitlines()}
       qnames_correct=qnames=={f'{sid}_pair{i}' for i in range(20)}
       with table.open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
       mean_col=next(k for k in rows[0] if k.lower().endswith('mean'));mean=float(rows[0][mean_col]);expected=4000/(12000-150)
       # SAMtools depth independently counts aligned bases, with the same documented75bp end exclusion.
       depth=subprocess.run([str(bow/'samtools'),'depth','-aa',str(bam)],capture_output=True,text=True,check=True).stdout
       included=[int(line.split('\t')[2]) for line in depth.splitlines() if 75<int(line.split('\t')[1])<=11925];independent=sum(included)/len(included)
       obs={'sample':sid,'kind':kind,'sq':sq,'mapped':mapped,'qnames_correct':qnames_correct,'coverage_rows':rows,'mean':mean,'independent_mean':independent,'expected_mean':expected};observations.append(obs)
       checks[f'{sid}_{kind}']=len(sq)==1 and sq[0]['SN']==sid+'_reference' and int(sq[0]['LN'])==12000 and mapped==40 and qnames_correct and len(rows)==1 and next(iter(rows[0].values()))==sid+'_reference' and math.isclose(mean,independent,rel_tol=1e-6,abs_tol=1e-7) and math.isclose(mean,expected,rel_tol=1e-6,abs_tol=1e-7)
     with (p/'trace.tsv').open() as f:tasks=list(csv.DictReader(f,delimiter='\t'))
     checks['fourteen_real_tasks']=len(tasks)==14 and all(x['status']=='COMPLETED' and x['exit']=='0' for x in tasks)
     for chain in ['COVERAGE','ABUNDANCE']:
      order=[x['name'] for x in tasks if ('BOWTIE2_BUILD_'+chain) in x['name']];checks['index_order_'+chain]=len(order)==2 and 'B.fa' in order[0] and 'A.fa' in order[1]
    receipt={'command':command,'exit':r.returncode,'checks':checks,'observations':observations,'pass':all(checks.values()),'source_sha256':{f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in ['subworkflows/contig_coverage.nf','subworkflows/plasmid_abundance.nf','conf/nfcore_upstream.config']},'limitations':['actual original coverage/abundance workflows+fixed native tools, synthetic distinguishable references/paired reads','short-read only; not minimap2, hybrid merge/long path, complete host-removal/platform E2E or biological accuracy benchmark']};(p/'run.json').write_text(json.dumps(receipt,indent=2)+'\n');print(checks);print(observations);return receipt['pass']


def host_components(root,base,source,binpath,nextflow):
    base.mkdir(parents=True,exist_ok=True)
    data=base/'data';data.mkdir(exist_ok=True)
    rng=random.Random(20261023);foreign=''.join(rng.choice('ACGT') for _ in range(4000));expected={}
    for sid in ['A','B']:
     (data/f'{sid}.fa').write_bytes((source/f'{sid}.fa').read_bytes())
     for mate in [1,2]:
      records=[]
      for i in range(5):
       start=100+400*i;seq=foreign[start:start+100] if mate==1 else foreign[start+200:start+300].translate(str.maketrans('ACGT','TGCA'))[::-1]
       records.append(f'@{sid}_foreign{i}/{mate}\n{seq}\n+\n'+('I'*100)+'\n')
      text=''.join(records);expected[(sid,mate)]=text;(data/f'{sid}_R{mate}.fq').write_text((source/f'{sid}_R{mate}.fq').read_text()+text)
    runs=[]
    for platform,output in [('illumina','ch_final_reads'),('hybrid','ch_final_short')]:
     p=base/platform;p.mkdir(exist_ok=True);source_text=(root/f'subworkflows/{platform}.nf').read_text();block=re.search(r'    ch_host_ref =.*?(?=    // ----------------)',source_text,re.S)[0];(p/'production-block.nf.txt').write_text(block)
     (p/'probe.nf').write_text(f'''nextflow.enable.dsl = 2
    include {{ BOWTIE2_BUILD as BOWTIE2_BUILD_HOST }} from '{root}/modules/nf-core/bowtie2/build/main'
    include {{ BOWTIE2_ALIGN as BOWTIE2_ALIGN_HOST }} from '{root}/modules/nf-core/bowtie2/align/main'
    workflow {{
        ch_reads = Channel.fromList(['A','B'].collect {{ id -> tuple([id:id,single_end:false,host_reference:'{data}/'+id+'.fa'],file('{data}/'+id+'_R1.fq'),file('{data}/'+id+'_R2.fq')) }})
        def ch_br = [host:ch_reads,nohost:Channel.empty()]
    {block}
        {output}.view {{ meta,r1,r2 -> 'HOST_FREE\\t'+meta.id+'\\t'+r1+'\\t'+r2 }}
    }}
    ''')
     (p/'config').write_text(f'''params.outdir = '{p}/out'
    params.publish_dir_mode = 'copy'
    includeConfig '{root}/conf/nfcore_upstream.config'
    process.executor = 'local'
    process.cpus = 1
    process.memory = '1 GB'
    executor.queueSize = 4
    process {{
        withName: 'BOWTIE2_BUILD_HOST' {{
            beforeScript = {{ meta.id == 'A' ? 'sleep 6' : 'sleep 0' }}
        }}
    }}
    conda.enabled = false
    docker.enabled = false
    singularity.enabled = false
    ''')
     env=os.environ.copy();env['PATH']=str(binpath)+':'+env['PATH'];command=[nextflow,'-C',str(p/'config'),'run',str(p/'probe.nf'),'-work-dir',str(p/'work'),'-with-trace',str(p/'trace.tsv'),'-ansi-log','false'];r=subprocess.run(command,env=env,text=True,capture_output=True);(p/'stdout.log').write_text(r.stdout);(p/'stderr.log').write_text(r.stderr);checks={'workflow_success':r.returncode==0};samples=[]
     if r.returncode==0:
      for sid in ['A','B']:
       out=p/'out/01_qc/host_removal/bowtie2';bam=out/f'{sid}.host.bam';header=subprocess.run([str(binpath/'samtools'),'view','-H',str(bam)],capture_output=True,text=True,check=True).stdout;sq=[dict(x.split(':',1) for x in line.split('\t')[1:]) for line in header.splitlines() if line.startswith('@SQ\t')];mapped=int(subprocess.run([str(binpath/'samtools'),'view','-c','-F','4',str(bam)],capture_output=True,text=True,check=True).stdout)
       sam_records=subprocess.run([str(binpath/'samtools'),'view',str(bam)],capture_output=True,text=True,check=True).stdout; qnames={line.split('\t')[0] for line in sam_records.splitlines()}; qnames_correct=qnames==({f'{sid}_pair{i}' for i in range(20)} | {f'{sid}_foreign{i}' for i in range(5)})
       counts=[];parity=[]
       for mate in [1,2]:
        observed=gzip.open(out/f'{sid}.host.unmapped_{mate}.fastq.gz','rt').read();counts.append(len(observed.splitlines())//4);parity.append(observed==expected[(sid,mate)])
       samples.append({'sample':sid,'sq':sq,'mapped_records':mapped,'qnames_correct':qnames_correct,'retained_pairs':counts,'exact_foreign_reads_only':all(parity)});checks[sid]=len(sq)==1 and sq[0]['SN']==sid+'_reference' and int(sq[0]['LN'])==12000 and mapped==40 and qnames_correct and counts==[5,5] and all(parity)
      tasks=list(csv.DictReader((p/'trace.tsv').open(),delimiter='\t'));builds=[x['name'] for x in tasks if 'BOWTIE2_BUILD_HOST' in x['name']];checks['four_completed_tasks']=len(tasks)==4 and all(x['status']=='COMPLETED' and x['exit']=='0' for x in tasks);checks['forced_inversion']='B.fa' in builds[0] and 'A.fa' in builds[1]
     runs.append({'platform_component':platform,'command':command,'exit':r.returncode,'checks':checks,'samples':samples,'production_source_sha256':hashlib.sha256(source_text.encode()).hexdigest(),'extracted_block_sha256':hashlib.sha256(block.encode()).hexdigest()});print(platform,checks,samples,flush=True)
     receipt={'runs':runs,'pass':all(all(x['checks'].values()) for x in runs),'limitations':['verbatim production host-removal component blocks with original build/align modules, not full ILLUMINA/HYBRID workflow','native fixed versions and synthetic host/nonhost truth; no FASTP, assembler, detector or full platform E2E']};(base/'run.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt['pass']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bowtie-prefix',required=True,type=Path)
    parser.add_argument('--coverage-prefix',required=True,type=Path)
    parser.add_argument('--work-dir',type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    nextflow=shutil.which('nextflow')
    if not nextflow:parser.error('nextflow must be on PATH')
    p=(args.work_dir or Path(tempfile.mkdtemp(prefix='native-pairing-'))).resolve()
    if p.exists() and any(p.iterdir()):parser.error('--work-dir must be an empty isolated directory')
    p.mkdir(parents=True,exist_ok=True)
    bow=args.bowtie_prefix.resolve()/'bin';cov=args.coverage_prefix.resolve()/'bin'
    versions={}
    for tool,directory,wanted in [('bowtie2',bow,'version 2.5.4'),('samtools',bow,'samtools 1.21'),('pigz',bow,'pigz 2.8'),('coverm',cov,'coverm 0.7.0'),('samtools',cov,'samtools 1.24')]:
        env=os.environ.copy();env['PATH']=str(directory)+':'+env['PATH']
        r=subprocess.run([str(directory/tool),'--version'],env=env,text=True,capture_output=True,check=True)
        first=(r.stdout+r.stderr).splitlines()[0]
        if not first.endswith(wanted):raise RuntimeError(f'{directory/tool}: expected {wanted}, got {first}')
        versions[str(directory/tool)]=first
    (p/'versions.json').write_text(json.dumps(versions,indent=2)+'\n')
    data=p/'data';data.mkdir()
    for sid,seed in [('A',20261021),('B',20261022)]:
        rng=random.Random(seed);seq=''.join(rng.choice('ACGT') for _ in range(12000))
        (data/f'{sid}.fa').write_text(f'>{sid}_reference\n{seq}\n')
        mates=[[],[]]
        for i in range(20):
            start=100+400*i
            for mate,s in enumerate([seq[start:start+100],seq[start+200:start+300].translate(str.maketrans('ACGT','TGCA'))[::-1]]):
                mates[mate].append(f'@{sid}_pair{i}/{mate+1}\n{s}\n+\n'+('I'*100)+'\n')
        for mate,records in enumerate(mates,1):(data/f'{sid}_R{mate}.fq').write_text(''.join(records))
    print('Native actual workflow/component regression; synthetic sequence truth. Artifacts:',p,flush=True)
    first=coverage_abundance(root,p/'production',data,bow,cov,nextflow)
    second=host_components(root,p/'host-components',data,bow,nextflow)
    return 0 if first and second else 1


if __name__=='__main__':raise SystemExit(main())
