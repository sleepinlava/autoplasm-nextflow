#!/usr/bin/env python3
"""Native Nextflow catalogue→paired remapping regression; synthetic interface data, no benchmark."""
import argparse,csv,json,os,random,subprocess,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'bin'))
from protocol_catalogue import fasta,rows
from build_shared_catalogue import write_tsv

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--outdir',type=Path,required=True);p.add_argument('--runtime-root',type=Path,required=True);p.add_argument('--python',type=Path,required=True);p.add_argument('--resume',action='store_true');a=p.parse_args()
a.outdir.mkdir(parents=True,exist_ok=a.resume)
rng=random.Random(20261030);shared=''.join(rng.choices('ACGT',k=3000));reference=shared
for i in range(1,4):
 d=a.outdir/'fixture'/f'sample{i}';d.mkdir(parents=True,exist_ok=a.resume);(d/'bins').mkdir(exist_ok=a.resume)
 dna=reference if i<3 else ''.join(rng.choices('ACGT',k=3000))
 if i==2:dna=dna[:1500]+('A' if dna[1500]!='A' else 'C')+dna[1501:]
 fasta(d/'assembly.fasta',[('node1',dna),('chromosome',''.join(rng.choices('ACGT',k=5000)))])
 if i<3:fasta(d/'bins/bin1.fna',[('node1',dna)])
 write_tsv(d/'summary.tsv',['seq_name','plasmid_score'],[['node1',.99]] if i<3 else [])
 write_tsv(d/'structure.tsv',['plasmid_id','topology_status'],[['node1','unknown']] if i<3 else [])
 mate=[[],[]]
 for j,start in enumerate([100,500,1000,2000]):
  sequences=[dna[start:start+100],dna[start+200:start+300].translate(str.maketrans('ACGT','TGCA'))[::-1]]
  for k,seq in enumerate(sequences):mate[k].append(f'@pair{j}/{k+1}\n{seq}\n+\n'+('I'*100)+'\n')
 for k in range(2):(d/f'R{k+1}.fastq').write_text(''.join(mate[k]))
paths=[a.python.parent,ROOT/'bin',a.runtime_root/'bowtie2-2.5.4/bin',a.runtime_root/'genomad-1.12.0/bin']
config=f'''params {{
    fixture = '{a.outdir.resolve()}/fixture'
    outdir = '{a.outdir.resolve()}/out'
    short_read_protocol = true
    catalogue_identity = 0.99
    catalogue_coverage = 0.9
    protocol_min_breadth = 0.1
    publish_dir_mode = 'copy'
}}
process {{
    executor = 'local'
    cpus = 1
    memory = '1 GB'
    withName: '.*' {{ cpus=1;memory='1 GB' }}
    withName: 'CATALOGUE_CLUSTER_COMPLETE|CATALOGUE_CLUSTER_CIRCULAR|CATALOGUE_CLUSTER_FRAGMENT' {{
        ext.args = '--min-seq-id 0.99 -c 0.9 --cov-mode 0 --cluster-mode 2 --seq-id-mode 0'
    }}
}}
conda.enabled = false
docker.enabled = false
trace.overwrite = true
report.overwrite = true
timeline.overwrite = true
'''
(a.outdir/'test.config').write_text(config)
env=os.environ.copy();env['PATH']=os.pathsep.join(map(str,paths))+os.pathsep+env['PATH'];env['NXF_OFFLINE']='true'
cmd=['nextflow','-log',str(a.outdir/'nextflow.log'),'-c',str(a.outdir/'test.config'),'run',str(ROOT/'tests/protocol/core.nf'),'-work-dir',str(a.outdir/'work'),'-with-trace',str(a.outdir/'trace.tsv'),'-ansi-log','false','-with-report',str(a.outdir/'out/pipeline_info/execution_report.html'),'-with-timeline',str(a.outdir/'out/pipeline_info/timeline.html')]
run_name='protocol_core_'+hashlib.sha256(str(a.outdir.resolve()).encode()).hexdigest()[:12]
if a.resume:cmd.extend(['-resume',run_name])
else:cmd.extend(['-name',run_name])
with (a.outdir/'console.log').open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
if r.returncode:print((a.outdir/'console.log').read_text());sys.exit(r.returncode)
cat=a.outdir/'out/catalogue/catalogue';features=rows(cat/'features.tsv')
assert sum(r['is_plasmid']=='1' for r in features)==1,features
ab=rows(a.outdir/'out/tables/plasmid_abundance.tsv');assert len(ab)==3,ab
counts={r['sample_id']:int(r['raw_count']) for r in ab};assert counts=={'sample1':4,'sample2':4,'sample3':0},counts
assert all(r['count_unit']=='proper_paired_fragment' for r in ab)
assert len(rows(cat/'candidate_evidence.tsv'))==2
summary={'status':'PASS','native_tool_scope':['MMseqs2','Bowtie2','SAMtools','pysam'], 'plasmid_counts':counts,'features':len(features),'scope':'synthetic wiring/count oracle; not a scientific performance benchmark'}
(a.outdir/'validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
