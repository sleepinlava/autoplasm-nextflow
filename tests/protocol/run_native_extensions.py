#!/usr/bin/env python3
"""Execute native production extension modules on small interface fixtures; no benchmark."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'bin'))
from build_shared_catalogue import records,write_tsv,file_digest
from protocol_catalogue import fasta,rows


def evolution_fixture(f):
    (f/'annotations').mkdir();(f/'systems').mkdir()
    rng=random.Random(31);amino='ACDEFGHIKLMNPQRSTVWY';genes=[];families=[];proteins=[]
    for family in range(3):
        ancestor=list(''.join(rng.choices(amino,k=150)))
        for taxon in range(4):
            seq=ancestor.copy()
            for pos in range(0 if taxon<2 else 10,150,17):seq[pos]=amino[(amino.index(seq[pos])+1+taxon//2)%20]
            for pos in rng.sample(range(150),3):seq[pos]=rng.choice(amino)
            gene=f'p{taxon}_g{family}'
            genes.append([gene,f'p{taxon}',family*500+1,family*500+450,'conserved protein'])
            families.append([f'family{family}',gene,f'p{taxon}']);proteins.append((gene,''.join(seq)))
    write_tsv(f/'annotations/genes.tsv',['gene_id','plasmid_id','start','end','product'],genes)
    write_tsv(f/'annotations/gene_family_clusters.tsv',['family_id','gene_id','plasmid_id'],families)
    write_tsv(f/'annotations/mobile_module_candidates.tsv',['plasmid_id','start','end'],[])
    write_tsv(f/'systems/membership.tsv',['plasmid_id','system_id','eligible_for_abundance'],[[f'p{i}','system_native',1] for i in range(4)]+[['q0','system_ineligible',1],['q1','system_ineligible',1]])
    fasta(f/'proteins.faa',proteins)


def qc_fixture(f):
    rng=random.Random(20261031);dna={name:''.join(rng.choices('ACGT',k=3000)) for name in ['host','nonhost']}
    fasta(f/'host.fasta',[('host',dna['host'])]);mates=[[],[]]
    for name,seq in dna.items():
        for i,start in enumerate([200,600,1200,2000]):
            pair=[seq[start:start+100],seq[start+200:start+300].translate(str.maketrans('ACGT','TGCA'))[::-1]]
            for mate,read in enumerate(pair):mates[mate].append(f'@{name}_{i}/{mate+1}\n{read}\n+\n'+('I'*100)+'\n')
    for mate in range(2):(f/f'R{mate+1}.fastq').write_text(''.join(mates[mate]))


def upstream_fixture(f,source):
    (f/'catalogue').mkdir()
    upstream=source/'test';dna=dict(records(upstream/'test-contigs.fa'))
    system=rows(upstream/'test-contigs-mobmess_systems.txt')[0]
    backbone=system['backbone_plasmids'].split('|')[0]
    # Use upstream-documented full-containment positive pairs, not arbitrary
    # members whose relationship may depend on omitted intermediate plasmids.
    parents=[r['reference'] for r in rows(upstream/'test-contigs-mobmess_ani.txt') if r['query']==backbone and r['reference']!=backbone and float(r['C'])>=.99 and float(r['I_local'])>=.99]
    selected=[backbone]+parents[:3]
    fasta(f/'catalogue/plasmids.fasta',((s,dna[s]) for s in selected))
    # This interface fixture supplies an upstream qualification result; it does
    # not establish independent molecule completeness from circular labels.
    write_tsv(f/'catalogue/structure.tsv',['plasmid_id','completeness'],[[s,'predicted_near_complete'] for s in selected])
    write_tsv(f/'abundance.tsv',['plasmid_id','sample_id','coverage','raw_count','tpm','rpkm'],[[s,'S1',10,5,100,50] for s in selected])
    (f/'upstream_identity.json').write_text(json.dumps({'commit':'97c0cfc0f810062e32dcf34f700b1fc8be8029a4','selected_ids':selected,'source_sha256':file_digest(upstream/'test-contigs.fa'),
        'qualification':'manually qualified interface fixture; not independent completeness validation'},indent=2))


def ancom_fixture(f,groups):
    rng=random.Random(31);data=[];metadata=[]
    subjects=[rng.uniform(.7,1.5) for _ in range(12)]
    for group in range(groups):
        for i in range(12):
            sid=f'S{group}_{i:02}';metadata.append([sid,chr(65+group),f'batch{i%2}',f'U{i:02}'])
            for feature in range(32):
                mean=(80+feature*7)*subjects[i]*(2 if group and feature<4 else 1)
                count=max(1,int(rng.gauss(mean,mean*.2)))
                if feature==31 and group==1:count=0
                data.append([f'P{feature:02}',sid,count,'proper_paired_fragment'])
    write_tsv(f/'abundance.tsv',['plasmid_id','sample_id','raw_count','count_unit'],data)
    write_tsv(f/'metadata.tsv',['sample_id','group','batch','subject'],metadata)


def amrfinder_fixture(f,source):
    (f/'catalogue').mkdir();(f/'systems').mkdir()
    dna=[('seq_'+hashlib.sha256(seq.encode()).hexdigest(),seq) for name,seq in records(source/'test_dna.fa')]
    fasta(f/'catalogue/plasmids.fasta',dna)
    write_tsv(f/'catalogue/features.tsv',['feature_id','length_bp','is_plasmid'],[[name,len(seq),1] for name,seq in dna])
    write_tsv(f/'catalogue/structure.tsv',['plasmid_id','completeness'],[[name,'not_established'] for name,seq in dna])
    write_tsv(f/'systems/membership.tsv',['plasmid_id','system_id','membership_grade'],[])
    write_tsv(f/'abundance.tsv',['plasmid_id','sample_id','breadth','coverage'],[[name,'native_sample',1,2] for name,seq in dna])
    (f/'upstream_identity.json').write_text(json.dumps({'commit':'9f0987075f2787ba0566a73e172c340aff63f8af','source':'ncbi/amr/test_dna.fa',
        'source_sha256':file_digest(source/'test_dna.fa'),'purpose':'native annotation interface; input is not a confirmed plasmid catalogue'},indent=2))


def strain_fixture(f):
    import pysam
    (f/'catalogue').mkdir();(f/'mags').mkdir();rng=random.Random(31)
    dna=''.join(rng.choices('ACGT',k=20000));fasta(f/'catalogue/reference.fasta',[('chromosome',dna)])
    write_tsv(f/'catalogue/features.tsv',['feature_id','length_bp','is_plasmid'],[['chromosome',20000,0]])
    write_tsv(f/'mags/scaffold_to_bin.tsv',['contig_id','mag_id'],[['chromosome','MAG1']])
    write_tsv(f/'mags/strain_eligible_mags.tsv',['mag_id','unique_locus_fraction'],[['MAG1',1]])
    for sample in ['sample1','sample2']:
        unsorted=f/(sample+'.unsorted.bam')
        with pysam.AlignmentFile(str(unsorted),'wb',header={'HD':{'VN':'1.6'},'SQ':[{'SN':'chromosome','LN':len(dna)}]}) as out:
            for number,start in enumerate(range(0,len(dna)-350,25)):
                for mate in range(2):
                    pos=start+200*mate;seq=dna[pos:pos+150]
                    # SAM/BAM stores SEQ in alignment orientation, including reverse reads.
                    r=pysam.AlignedSegment();r.query_name=f'read{number}';r.query_sequence=seq;r.flag=99 if mate==0 else 147;r.reference_id=0;r.reference_start=pos;r.mapping_quality=1 if mate==1 and number%50==0 else 60;r.cigar=[(0,150)];r.next_reference_id=0;r.next_reference_start=start+200*(1-mate);r.template_length=350 if mate==0 else -350;r.query_qualities=pysam.qualitystring_to_array('I'*150);r.set_tag('NM',0);r.set_tag('MD','150');out.write(r)
        pysam.sort('-o',str(f/(sample+'.bam')),str(unsorted));unsorted.unlink()


def validate(component,base):
    out=base/'out'
    if component=='qc':
        from protocol_input_audit import names
        audit=out/'00_manifest/native_qc.input_audit';checksums=rows(audit/'checksums.tsv')
        assert len(checksums)==2 and all(int(r['pairs'])==8 for r in checksums)
        assert [r['sha256'] for r in checksums]==[file_digest(base/f'fixture/R{i}.fastq') for i in [1,2]]
        assert len(rows(audit/'seqkit_stats.tsv'))==2
        final=out/'01_qc/host_removal/paired'
        for mate in [1,2]:assert set(names(final/f'native_qc.hostfree_{mate}.fastq.gz'))=={f'nonhost_{i}' for i in range(4)}
        r=rows(out/'01_qc/retention/native_qc.retention.tsv')[0]
        assert [int(r[k]) for k in ['raw_reads','post_fastp_reads','post_host_reads']]==[16,16,8]
        assert float(r['host_step_retention'])==.5
        return {'raw_pairs':8,'post_host_pairs':4,'host_step_retention':.5,'native_tools':['SeqKit','fastp','Bowtie2','SAMtools']}
    if component=='evolution':
        folder=out/'09_comparative_genomics/evolution/evolution';state=json.loads((folder/'status.json').read_text())
        assert next(r for r in state['systems'] if r['system_id']=='system_native')['status']=='measured'
        assert next(r for r in state['systems'] if r['system_id']=='system_ineligible')['status']=='ineligible'
        tree=(folder/'system_native/backbone.treefile').read_text();assert all(f'p{i}:' in tree for i in range(4))
        assert 'q0' not in tree and 'q1' not in tree
        return {'systems':state['systems'],'tree_bytes':len(tree)}
    if component=='protein_families':
        from collections import Counter
        paths=list((out/'09_comparative_genomics/protein_families').glob('*_cluster.tsv'));assert len(paths)==1
        with paths[0].open() as stream:membership=list(csv.reader(stream,delimiter='\t'))
        counts=Counter(r[0] for r in membership)
        assert len(membership)==12 and len(counts)==3 and set(counts.values())=={4}
        assert {r[1] for r in membership}=={f'p{i}_g{j}' for i in range(4) for j in range(3)}
        return {'families':len(counts),'proteins':len(membership)}
    if component=='mobmess':
        folder=out/'09_comparative/mobmess/systems';systems=rows(folder/'systems.tsv');membership=rows(folder/'membership.tsv')
        assert systems and len({r['plasmid_id'] for r in membership})==4
        assert all(not r['system_id'] or r['system_id'] in {s['system_id'] for s in systems} for r in membership)
        return {'systems':len(systems),'members':len(membership),'system_count_rows':len(rows(out/'tables/system_abundance.tsv'))}
    if component=='mostplas':
        folder=out/'07_host_prediction/mostplas/mostplas';state=json.loads((folder/'status.json').read_text());assert state['status']=='measured'
        predicted=rows(folder/'host_range.tsv');expected={r['plasmid_id'] for r in rows(base/'fixture/catalogue/structure.tsv') if r['completeness'] in ('independently_supported','predicted_near_complete')}
        assert {r['plasmid_id'] for r in predicted}==expected
        return {'predicted_sequences':len(predicted),'model_sha256':state['model_sha256']}
    if component=='ancombc2':
        folder=out/'11_diversity/ancombc2/ancombc2';state=json.loads((folder/'status.json').read_text());assert state['status']=='measured'
        assert state['versions']['ANCOMBC']=='2.8.0',state['versions']
        coefficients=rows(folder/'coefficients.tsv');assert coefficients and any(k.startswith('lfc_') for k in coefficients[0])
        assert all(float(r['ci_low_groupB'])<float(r['lfc_groupB'])<float(r['ci_high_groupB']) for r in coefficients if r['lfc_groupB'] not in ('','NA'))
        assert any(math.isfinite(float(r['lfc_groupB'])) and math.isfinite(float(r['q_groupB'])) for r in coefficients if r['lfc_groupB'] not in ('','NA') and r['q_groupB'] not in ('','NA'))
        global_results=rows(folder/'global.tsv')
        if state['tests']['global']:
            assert global_results and rows(folder/'pairwise.tsv')
            assert any(r['p_val'] not in ('','NA') and math.isfinite(float(r['p_val'])) for r in global_results)
        else:assert not global_results and not rows(folder/'pairwise.tsv')
        return {'features_tested':len(coefficients),'versions':state['versions'],'sample_count':len(state['sample_ids']),'random_formula':state['random_formula'],'tests':state['tests']}
    if component=='amrfinderplus':
        folder=out/'08_annotation/integrated/annotations'
        raw=rows(folder/'amrfinder_hits.tsv');typed=rows(folder/'amrfinder_elements.tsv')
        assert raw and len(raw)==len(typed)
        assert {r['element_type'] for r in typed}=={'AMR','STRESS','VIRULENCE'}
        assert all(r['method'] and r['evidence_grade']!='uncertain_match' for r in typed)
        args={r['gene'] for r in typed if r['element_type']=='AMR'}
        assert {r['arg'] for r in rows(folder/'sample_ARG_matrix.tsv')}==args
        assert sum(int(r['gene_hits']) for r in rows(folder/'plasmid_ARG_matrix.tsv'))==sum(r['element_type']=='AMR' for r in typed)
        assert json.loads((folder/'status.json').read_text())['amrfinder_status']=='measured'
        commands=list((out/'08_annotation/amrfinderplus').glob('*.task_command.sh'))
        assert len(commands)==1 and '--plus' in commands[0].read_text()
        identity=json.loads(next(line.split('\t',1)[1] for line in (base/'console.log').read_text().splitlines() if line.startswith('AMRFINDER_DATABASE_IDENTITY\t')))
        assert len(identity['sha256'])==64 and identity['file_count']>0 and identity['bytes']>0
        return {'native_hits':len(raw),'AMR_hits':sum(r['element_type']=='AMR' for r in typed),'element_types':sorted({r['element_type'] for r in typed}),'database_identity':identity}
    if component=='strain':
        import pysam
        qualified={p.resolve() for p in (base/'work').rglob('*.qualified.bam')}
        assert len(qualified)==2
        for path in qualified:
            with pysam.AlignmentFile(str(path),'rb') as stream:
                reads=list(stream.fetch(until_eof=True))
            assert len(reads)==1540 and all(int(r.query_name[4:])%50!=0 for r in reads)
        folder=out/'08_epidemiology/instrain/strain_compare';table=list(folder.rglob('*genomeWide_compare.tsv'));assert len(table)==1
        comparisons=rows(table[0]);assert comparisons
        matched=[r for r in comparisons if r['name1']!=r['name2'] and r['genome']=='M:MAG1'];assert matched
        assert all(float(r['popANI'])>=.99999 and int(r['compared_bases_count'])>=10000 for r in matched)
        names=rows(folder/'sample_identity.tsv');assert {r['sample_id'] for r in names}=={'sample1','sample2'}
        return {'cross_sample_comparisons':len(matched),'compared_bases':[int(r['compared_bases_count']) for r in matched],'eligible_pairs_per_sample':770,'low_MAPQ_pairs_excluded_per_sample':16}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--component',choices=['qc','protein_families','evolution','mobmess','mostplas','ancombc2','strain','amrfinderplus'],required=True);p.add_argument('--outdir',type=Path,required=True);p.add_argument('--runtime',type=Path,required=True);p.add_argument('--source',type=Path);p.add_argument('--sequence-source',type=Path);p.add_argument('--random-formula',default='');p.add_argument('--groups',type=int,default=3,choices=[2,3]);p.add_argument('--database',type=Path);a=p.parse_args()
    a.outdir=a.outdir.resolve();a.outdir.mkdir(parents=True);f=a.outdir/'fixture';f.mkdir()
    if a.component=='qc':qc_fixture(f)
    elif a.component in ['evolution','protein_families']:evolution_fixture(f)
    elif a.component in ['mobmess','mostplas']:upstream_fixture(f,a.sequence_source or a.source)
    elif a.component=='ancombc2':ancom_fixture(f,a.groups)
    elif a.component=='amrfinderplus':amrfinder_fixture(f,a.source)
    else:strain_fixture(f)
    config=f'''params {{ component='{a.component}'; protocol_strain=true; amrfinderplus_db='{a.database}'; fixture='{f}'; outdir='{a.outdir}/out'; publish_dir_mode='copy'; protocol_tree_min_members=4;protocol_tree_min_core=3; mostplas_source='{a.source}';mostplas_threshold=0.4;ancombc2_formula='group + batch';ancombc2_random_formula='{a.random_formula}';ancombc2_prevalence=0.1;min_group_replicates=3;protocol_strain_min_coverage=5;protocol_min_breadth=0.75 }}
process {{ withName: '.*' {{cpus=2;memory='4 GB';time='30 min'}} }}
conda.enabled=false
docker.enabled=false
report.enabled=false
timeline.enabled=false
'''
    if a.component=='qc':config+=f"\nprocess {{ withName: 'PROTOCOL_INPUT_AUDIT' {{ publishDir=[path:'{a.outdir}/out/00_manifest',mode:'copy'] }} }}\n"
    if a.component=='protein_families':config+=f"\nprocess {{ withName: 'PROTOCOL_PROTEIN_FAMILIES' {{ publishDir=[path:'{a.outdir}/out/09_comparative_genomics/protein_families',mode:'copy'] }} }}\n"
    (a.outdir/'native.config').write_text(config);env=os.environ.copy();env['PATH']=str(a.runtime.resolve()/'bin')+os.pathsep+env['PATH'];env.update(NXF_OFFLINE='true',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2')
    name='native_'+a.component+'_'+hashlib.sha256(str(a.outdir).encode()).hexdigest()[:10]
    command=['nextflow','-log',str(a.outdir/'nextflow.log'),'-c',str(a.outdir/'native.config'),'run',str(ROOT/'tests/protocol/native_extensions.nf'),'-name',name,'-work-dir',str(a.outdir/'work'),'-with-trace',str(a.outdir/'trace.tsv'),'-ansi-log','false','--outdir',str(a.outdir/'out')]
    if a.component in ['amrfinderplus','protein_families']:command[command.index('-name'):command.index('-name')]=['-profile','short_read_protocol']
    (a.outdir/'command.json').write_text(json.dumps(command,indent=2))
    with (a.outdir/'console.log').open('w') as log:result=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:print('\n'.join((a.outdir/'console.log').read_text().splitlines()[-60:]));return result.returncode
    evidence=validate(a.component,a.outdir)
    summary={'status':'PASS','component':a.component,'scope':'native interface integration; not a scientific performance benchmark','evidence':evidence}
    (a.outdir/'validation.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));return 0

if __name__=='__main__':sys.exit(main())
