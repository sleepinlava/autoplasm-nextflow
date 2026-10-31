"""Protocol entity, measurement, coordinate and inference regression cases (not a benchmark)."""
import csv
import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'bin'))
import protocol_catalogue as cat
import protocol_systems as systems
import protocol_hosts as hosts
import protocol_annotation as ann
from build_shared_catalogue import write_tsv,canonical,digest
from collect_shared_abundance import collect


class ProtocolProducts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.d=Path(self.temp.name)

    def make_catalogue(self):
        rng=random.Random(410);dna=[''.join(rng.choices('ACGT',k=1000)) for _ in range(3)]
        assembly=self.d/'assembly.fa';cat.fasta(assembly,zip(['a','b','c'],dna))
        bins=self.d/'bins';bins.mkdir();cat.fasta(bins/'bin7.fna',zip(['a','b'],dna[:2]))
        summary=self.d/'summary.tsv';write_tsv(summary,['seq_name','plasmid_score'],[['a',.99],['c',.95]])
        structure=self.d/'structure.tsv';write_tsv(structure,['plasmid_id','topology_status'],[['a','circular_candidate'],['c','unknown']])
        candidate=self.d/'candidate';cat.integrate(assembly,bins,summary,structure,'001',candidate)
        exact=self.d/'exact';cat.prepare(['001'],[assembly],[candidate/'candidates.fasta'],[candidate/'evidence.tsv'],exact)
        out=self.d/'catalogue';cat.finalize(exact,[],out,.99,.9)
        return out,dna,candidate

    def test_raw_pair_order_and_original_compressed_byte_checksums(self):
        import gzip
        from protocol_input_audit import audit
        from build_shared_catalogue import file_digest
        r1=self.d/'R1.fastq';r2=self.d/'R2.fastq.gz'
        first='@readA/1\nACGT\n+\nIIII\n';second='@readB/1\nTGCA\n+\nIIII\n'
        r1.write_text(first+second)
        with gzip.open(r2,'wt') as stream:stream.write((first+second).replace('/1','/2'))
        output=self.d/'audit';audit('S',[r1,r2],output)
        checks=cat.rows(output/'checksums.tsv');self.assertEqual([r['pairs'] for r in checks],['2','2'])
        self.assertEqual([r['sha256'] for r in checks],[file_digest(r1),file_digest(r2)])
        with gzip.open(r2,'wt') as stream:stream.write((second+first).replace('/1','/2'))
        with self.assertRaisesRegex(ValueError,'paired FASTQ IDs/order differ'):
            audit('S',[r1,r2],self.d/'mismatch')

    def test_bin_is_primary_supplement_not_double_counted_and_entities_preserved(self):
        out,dna,candidate=self.make_catalogue();evidence=cat.rows(candidate/'evidence.tsv')
        self.assertEqual(len(evidence),3)
        self.assertEqual([r['origin'] for r in evidence],['plasmaag_bin','plasmaag_bin','genomad_supplement'])
        self.assertEqual(evidence[0]['entity_id'],evidence[1]['entity_id'])
        self.assertNotEqual(evidence[0]['entity_id'],evidence[2]['entity_id'])
        self.assertTrue(all(r['completeness']=='not_established' for r in evidence))
        self.assertEqual(len(dict(cat.records(out/'plasmids.fasta'))),3)
        self.assertEqual(len(dict(cat.records(out/'fragments.fasta'))),2)
        self.assertTrue(all(r['feature_id'].startswith('seq_') for r in cat.rows(out/'candidate_evidence.tsv')))

    def test_near_duplicate_reference_and_source_mapping_stay_consistent(self):
        out,dna,candidate=self.make_catalogue();exact=self.d/'exact';features=cat.rows(exact/'features.tsv')
        # Two same-stratum fragments deliberately declared a cluster by the external-tool fixture.
        fragments=list(dict(cat.records(exact/'fragment.fasta')))
        cluster=self.d/'cluster.tsv';cluster.write_text(f'{fragments[0]}\t{fragments[0]}\n{fragments[0]}\t{fragments[1]}\n')
        merged=self.d/'merged';cat.finalize(exact,[cluster],merged,.99,.9)
        self.assertEqual(len(cat.rows(merged/'features.tsv')),2)
        self.assertEqual({r['feature_id'] for r in cat.rows(merged/'sources.tsv')},set(dict(cat.records(merged/'reference.fasta'))))
        self.assertEqual(sum(r['relation']=='near_duplicate' for r in cat.rows(merged/'members.tsv')),1)
        self.assertIn('alignment_required',{r['orientation'] for r in cat.rows(merged/'sources.tsv')})

    def test_predicted_near_complete_gate_requires_combined_evidence(self):
        out,dna,_=self.make_catalogue();bins=self.d/'bins'
        cat.fasta(bins/'bin7.fna',[('a',dna[0])])
        write_tsv(bins/'bin_evidence.tsv',['bin_id','plasmid_score','graph_support'],[['bin7',.98,'assembly_graph_available_not_independently_validated']])
        target=self.d/'qualified';cat.integrate(self.d/'assembly.fa',bins,self.d/'summary.tsv',self.d/'structure.tsv','001',target)
        a=next(r for r in cat.rows(target/'evidence.tsv') if r['contig_id']=='a');self.assertEqual(a['completeness'],'predicted_near_complete')
        # Keep the same high score and circularity, but restore an unresolved
        # multi-contig bin: this must not certify a near-complete molecule.
        cat.fasta(bins/'bin7.fna',zip(['a','b'],dna[:2]))
        target=self.d/'unqualified';cat.integrate(self.d/'assembly.fa',bins,self.d/'summary.tsv',self.d/'structure.tsv','001',target)
        a=next(r for r in cat.rows(target/'evidence.tsv') if r['contig_id']=='a');self.assertEqual(a['completeness'],'not_established')

    def test_independent_completeness_is_a_separate_clustering_stratum(self):
        out,dna,candidate=self.make_catalogue()
        fid='seq_'+digest(canonical(dna[0])[0]);known=self.d/'complete_ids';known.write_text(fid+'\n')
        exact=self.d/'supported_exact';cat.prepare(['001'],[self.d/'assembly.fa'],[candidate/'candidates.fasta'],[candidate/'evidence.tsv'],exact,known)
        self.assertEqual(set(dict(cat.records(exact/'complete.fasta'))),{fid})
        self.assertNotIn(fid,dict(cat.records(exact/'fragment.fasta')))
        final=self.d/'supported';cat.finalize(exact,[],final,.99,.9,known)
        self.assertEqual({r['plasmid_id'] for r in cat.rows(final/'structure.tsv') if r['completeness']=='independently_supported'},{fid})

    def test_plsdb_union_coverage_does_not_sum_overlapping_HSPs(self):
        path=self.d/'hits';path.write_text('p\tr\t99.9\t600\t1\t600\t1\t600\t1000\t1000\t0\t900\n'+'p\tr\t99.9\t500\t400\t900\t400\t900\t1000\t1000\t0\t800\n')
        labels=self.d/'labels';write_tsv(labels,['reference_id','host_taxonomy'],[['r','genus_A']])
        out=self.d/'hosts';hosts.plsdb(path,labels,out,.99,.95)
        self.assertEqual(cat.rows(out),[])
        hosts.plsdb(path,labels,out,.99,.9);self.assertEqual(float(cat.rows(out)[0]['query_coverage']),.9)

    def test_system_fragments_and_multisystem_members_are_not_inflated(self):
        out,_,_=self.make_catalogue();fids=sorted(dict(cat.records(out/'plasmids.fasta')))
        write_tsv(out/'structure.tsv',['plasmid_id','structure_grade','completeness'],[[fid,'near_complete_candidate' if fid==fids[0] else 'fragment_or_unknown','independently_supported' if fid==fids[0] else 'not_established'] for fid in fids])
        native=self.d/'native';native.mkdir()
        write_tsv(native/'mobmess_systems.txt',['system_name','backbone_plasmids','compound_plasmids'],[['PS1',fids[0],fids[1]],['PS2',fids[1],fids[0]]])
        write_tsv(native/'mobmess_contigs.txt',['contig','systems','cluster_type'],[[fids[0],'PS1','backbone'],[fids[1],'PS1|PS2','compound'],[fids[2],'PS1','fragment']])
        target=self.d/'systems';systems.normalize(native,out,target)
        member=cat.rows(target/'membership.tsv');self.assertEqual(sum(int(r['eligible_for_abundance']) for r in member),1)
        self.assertEqual(member[-1]['membership_grade'],'fragment_linked')
        abundance=self.d/'ab';write_tsv(abundance,['plasmid_id','sample_id','coverage','raw_count','tpm','rpkm'],[[p,'001',10,7,5,4] for p in fids])
        aggregated=self.d/'system_ab';systems.aggregate(abundance,target,aggregated)
        self.assertEqual(sum(int(r['raw_count']) for r in cat.rows(aggregated)),7)

    def test_shared_MAG_loci_do_not_create_full_genome_strain_eligibility(self):
        out,dna,_=self.make_catalogue();sources=cat.rows(out/'sources.tsv');ids={r['contig_id']:r['feature_id'] for r in sources}
        features=cat.rows(out/'features.tsv')
        for r in features:r['is_plasmid']='0'
        write_tsv(out/'features.tsv',list(features[0]),([r[k] for k in features[0]] for r in features))
        for cid in ['b','c']:sources.append(dict(sources[['a','b','c'].index(cid)],sample_id='002',contig_id=cid+'2'))
        write_tsv(out/'sources.tsv',list(sources[0]),([r[k] for k in sources[0]] for r in sources))
        one=self.d/'M1.fna';two=self.d/'M2.fna';cat.fasta(one,[('a',dna[0]),('b',dna[1])]);cat.fasta(two,[('b2',dna[1]),('c2',dna[2])])
        quality=self.d/'quality';write_tsv(quality,['Name','Completeness','Contamination'],[['M1',95,1],['M2',95,1]])
        spec=self.d/'spec';spec.write_text(json.dumps([{'sample_id':'001','bins':[str(one)],'quality':str(quality),'taxonomy':[]},{'sample_id':'002','bins':[str(two)],'quality':str(quality),'taxonomy':[]}]))
        ab=self.d/'ab';write_tsv(ab,['contig_id','sample_id','coverage','breadth','raw_count'],[[fid,sample,5,1,1] for fid in ids.values() for sample in ['001','002']])
        target=self.d/'mags';hosts.mags(spec,out,ab,target,50,10,.75)
        measured=cat.rows(target/'mag_abundance.tsv');self.assertEqual(len(measured),4)
        self.assertTrue(all(float(r['unique_locus_fraction'])==.5 for r in measured))
        self.assertEqual(cat.rows(target/'strain_eligible_mags.tsv'),[])
        self.assertEqual(len(cat.rows(target/'scaffold_to_bin.tsv')),2)
        flags=cat.rows(target/'MAG_quality_flags.tsv')
        self.assertTrue(all(r['mimag_quality']=='medium_quality' for r in flags))
        self.assertTrue(all(r['high_quality_completeness_contamination_candidate']=='1' for r in flags))
        self.assertTrue(all(r['rna_requirement_status']=='not_assessed_no_high_quality_certification' for r in flags))

    def test_strata_and_subject_gates_do_not_pool_repeated_samples(self):
        md=self.d/'md';write_tsv(md,['sample_id','group','subject'],[['a','G','U'],['b','G','U'],['c','G','V']])
        ab=self.d/'ab';write_tsv(ab,['plasmid_id','sample_id','raw_count'],[['p',s,n] for s,n in [('a',1),('b',2),('c',3)]])
        mags=self.d/'mags';mags.mkdir();write_tsv(mags/'mag_abundance.tsv',['mag_id','sample_id','raw_count'],[['m',s,n] for s,n in [('a',2),('b',3),('c',1)]])
        output=self.d/'matrices';hosts.host_matrix(ab,mags,md,output,'group','subject',3,.1)
        state=json.loads((output/'status.json').read_text())['cohorts'][0]
        self.assertEqual(state['sample_ids'],['a','c']);self.assertFalse(state['eligible']);self.assertEqual(list(output.glob('*.tsv')),[])

    def test_ARG_context_coordinates_overlap_distance_and_boundary(self):
        out,dna,_=self.make_catalogue();fid=sorted(dict(cat.records(out/'plasmids.fasta')))[0]
        sy=self.d/'systems';sy.mkdir();write_tsv(sy/'membership.tsv',['plasmid_id','system_id','membership_grade'],[])
        gff=self.d/'gff';gff.write_text(f'{fid}\tBakta\tCDS\t100\t200\t.\t+\t0\tID=gene1;product=protein\n')
        args=self.d/'args';write_tsv(args,['Contig id','Start','Stop','Strand','Element symbol','Type','Subtype','Method'],[[fid,100,200,'+','blaX','AMR','AMR','ALLELEX']])
        ises=self.d/'ises';ises.mkdir();write_tsv(ises/'native.csv',['seqID','isBegin','isEnd','family'],[[fid,180,220,'IS1']])
        ab=self.d/'ab';write_tsv(ab,['plasmid_id','sample_id','breadth','coverage'],[[fid,'001',1,1]])
        target=self.d/'annotations';ann.integrate(out,sy,[gff],[args],[ises],[],[],[],[],ab,target,100)
        context=cat.rows(target/'ARG_context.tsv')[0]
        self.assertEqual(context['nearest_mge_distance_bp'],'0');self.assertEqual(context['boundary_truncated'],'1')
        self.assertEqual(cat.rows(target/'sample_ARG_matrix.tsv')[0]['detected_plasmids'],'1')

    def test_amrfinder_plus_preserves_typed_hits_methods_and_ARG_only_matrices(self):
        catalogue,_,_=self.make_catalogue();fids=sorted(dict(cat.records(catalogue/'plasmids.fasta')));fid=fids[0]
        sy=self.d/'systems';sy.mkdir();write_tsv(sy/'membership.tsv',['plasmid_id','system_id','membership_grade'],[[fid,'SYS','system_member']])
        report=self.d/'amr.tsv'
        fields=['Contig id','Start','Stop','Strand','Element symbol','Type','Subtype','Scope','Method','Subclass','% Identity to reference']
        write_tsv(report,fields,[[fid,100,200,'+','blaX','AMR','AMR','core','ALLELEX','BETA-LACTAM',100],
            [fid,300,400,'-','virX','VIRULENCE','VIRULENCE','plus','BLASTX','',95],
            [fid,500,600,'+','stressX','STRESS','METAL','plus','PARTIAL_CONTIG_ENDX','',98]])
        abundance=self.d/'ab';write_tsv(abundance,['plasmid_id','sample_id','breadth','coverage'],[[p,'S',1,2] for p in fids])
        mobility=self.d/'mob.tsv';write_tsv(mobility,['sample_id','predicted_mobility'],[[p,'non-mobilizable'] for p in fids])
        output=self.d/'annotations';ann.integrate(catalogue,sy,[],[report],[],[],[mobility],[],[],abundance,output,50)
        typed=cat.rows(output/'amrfinder_elements.tsv');self.assertEqual([r['element_type'] for r in typed],['AMR','VIRULENCE','STRESS'])
        self.assertEqual([r['evidence_grade'] for r in typed],['exact_reference_match','homology_candidate','partial_match'])
        self.assertEqual(cat.rows(output/'amrfinder_hits.tsv')[1]['% Identity to reference'],'95')
        self.assertEqual({r['arg'] for r in cat.rows(output/'ARG_context.tsv')},{'blaX'})
        matrix=cat.rows(output/'plasmid_ARG_matrix.tsv');self.assertEqual(len(matrix),3)
        self.assertEqual(sum(int(r['gene_hits']) for r in matrix),1)
        self.assertEqual({r['arg'] for r in cat.rows(output/'sample_ARG_matrix.tsv')},{'blaX'})
        self.assertEqual(cat.rows(output/'system_ARG_matrix.tsv')[0]['positive_plasmids'],'1')
        self.assertEqual({r['evidence_grade'] for r in cat.rows(output/'mobility.tsv')},{'insufficient_fragment_evidence'})

    def test_eggnog_functions_reach_systems_and_only_detected_samples(self):
        catalogue,_,_=self.make_catalogue();fids=sorted(dict(cat.records(catalogue/'plasmids.fasta')))
        sy=self.d/'systems';sy.mkdir();write_tsv(sy/'membership.tsv',['plasmid_id','system_id','membership_grade'],[[p,'SYS','system_member'] for p in fids[:2]])
        gff=self.d/'genes.gff';gff.write_text(''.join(f'{p}\tBakta\tCDS\t100\t200\t.\t+\t0\tID=gene{i};product=protein\n' for i,p in enumerate(fids[:2])))
        eggnog=self.d/'eggnog.annotations';eggnog.write_text('## upstream metadata\n#query\tCOG_category\tKEGG_ko\ngene0\tEG\tko:K00001\ngene1\tG\tko:K00001\n')
        abundance=self.d/'ab';write_tsv(abundance,['plasmid_id','sample_id','breadth','coverage'],[[p,s,1 if i==0 or s=='S2' else .1,2] for i,p in enumerate(fids) for s in ['S1','S2']])
        output=self.d/'annotations';ann.integrate(catalogue,sy,[gff],[],[],[],[],[eggnog],[],abundance,output,50)
        system=cat.rows(output/'system_function_summary.tsv');g=next(r for r in system if r['term']=='G')
        self.assertEqual(g['positive_plasmids'],'2');self.assertEqual(g['annotated_genes'],'2')
        self.assertEqual({r['term'] for r in system if r['source']=='COG_category'},{'E','G'})
        samples={r['sample_id']:r for r in cat.rows(output/'sample_function_summary.tsv') if r['term']=='G'}
        self.assertEqual(samples['S1']['positive_plasmids'],'1');self.assertEqual(samples['S2']['positive_plasmids'],'2')

    def test_gene_adjacencies_capture_orientation_but_ignore_whole_reverse_complement(self):
        catalogue,_,_=self.make_catalogue();fids=sorted(dict(cat.records(catalogue/'plasmids.fasta')))
        sy=self.d/'systems';sy.mkdir();write_tsv(sy/'membership.tsv',['plasmid_id','system_id','membership_grade'],[[p,'SYS','system_member'] for p in fids])
        gff=self.d/'genes.gff';lines=[];families=[]
        orders=[[(0,'+'),(1,'+'),(2,'+')],[(0,'+'),(1,'-'),(2,'+')],[(2,'-'),(1,'-'),(0,'-')]]
        for p,order in zip(fids,orders):
            for i,(family,strand) in enumerate(order):
                gene=f'{p}_F{family}';families.append([f'F{family}',gene])
                lines.append(f'{p}\tBakta\tCDS\t{20+i*100}\t{90+i*100}\t.\t{strand}\t0\tID={gene};product=protein\n')
        gff.write_text(''.join(lines));cluster=self.d/'cluster.tsv';cluster.write_text(''.join('\t'.join(r)+'\n' for r in families))
        ab=self.d/'ab';write_tsv(ab,['plasmid_id','sample_id','breadth','coverage'],[[p,'S',1,2] for p in fids])
        output=self.d/'annotations';ann.integrate(catalogue,sy,[gff],[],[],[],[],[],[cluster],ab,output,50)
        variants=cat.rows(output/'system_structural_variants.tsv')
        self.assertTrue(variants);self.assertEqual({r['query_plasmid'] for r in variants},{fids[1]})
        self.assertTrue(any(r['strand_a']!=r['strand_b'] for r in variants))


class PairedMeasurements(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('pysam'),'pysam is required for native BAM tests')
    def test_pair_eligibility_overlap_breadth_and_count_unit(self):
        import pysam
        import protocol_quantification as quant
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);catalogue=d/'catalogue';catalogue.mkdir()
            write_tsv(catalogue/'features.tsv',['feature_id','length_bp','is_plasmid'],[['p',1000,1]])
            write_tsv(catalogue/'samples.tsv',['sample_id'],[['S']])
            bam=d/'reads.bam'
            with pysam.AlignmentFile(str(bam),'wb',header={'HD':{'VN':'1.6'},'SQ':[{'SN':'p','LN':1000}]}) as out:
                for name,mqs,flags in [('good',(40,40),(99,147)),('lowmate',(40,1),(99,147)),('discordant',(40,40),(65,129)),('mismatch',(40,40),(99,147))]:
                    for mate in range(2):
                        r=pysam.AlignedSegment();r.query_name=name;r.query_sequence='A'*100;r.flag=flags[mate];r.reference_id=0;r.reference_start=100+50*mate;r.mapping_quality=mqs[mate];r.cigar=[(0,100)];r.next_reference_id=0;r.next_reference_start=100+50*(1-mate);r.template_length=150 if mate==0 else -150;r.query_qualities=pysam.qualitystring_to_array('I'*100);r.set_tag('NM',10 if name=='mismatch' else 0);out.write(r)
            sorted_bam=d/'sorted.bam';pysam.sort('-o',str(sorted_bam),str(bam))
            filtered=d/'qualified.bam';result=d/'paired.tsv';quant.measure(sorted_bam,catalogue,'S',result,filtered_bam=filtered)
            r=cat.rows(result)[0];self.assertEqual(int(r['paired_fragments']),1);self.assertAlmostEqual(float(r['breadth']),.15);self.assertAlmostEqual(float(r['coverage']),.15);self.assertEqual(float(r['median_depth']),0)
            self.assertEqual(json.loads(result.with_suffix('.mapping_stats.json').read_text())['mismatch_filtered_pairs'],1)
            # The original alignment is a declared input; indexing must not mutate it.
            self.assertFalse(Path(str(sorted_bam)+'.bai').exists())
            with pysam.AlignmentFile(str(filtered),'rb') as stream:
                self.assertEqual([r.query_name for r in stream.fetch(until_eof=True)],['good','good'])

if __name__=='__main__':unittest.main()


class DeliveryProducts(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('weasyprint'),'weasyprint is required for native delivery tests')
    def test_B_and_C_candidates_require_taxonomy_and_shared_MGE_context(self):
        import protocol_delivery as delivery
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);c=d/'catalogue';s=d/'systems';ann=d/'annotations';m=d/'mags';host=d/'host'
            for path in [c,s,ann,m,host]:path.mkdir()
            shared='ACGT'*100;module='module_'+digest(canonical(shared)[0])[:24]
            cat.fasta(c/'plasmids.fasta',[('pA',shared+'A'*800),('pB',shared+'C'*800)])
            write_tsv(c/'features.tsv',['feature_id','length_bp'],[['pA',1200],['pB',1200]])
            write_tsv(c/'structure.tsv',['plasmid_id','structure_grade','completeness'],[[p,'near_complete_candidate','predicted_near_complete'] for p in ['pA','pB']])
            write_tsv(c/'candidate_evidence.tsv',['feature_id','sample_id','identity_grade'],[['pA','S1','high_confidence_bin'],['pB','S2','high_confidence_bin']])
            write_tsv(s/'membership.tsv',['plasmid_id','system_id','membership_grade','eligible_for_abundance'],[['pA','SYS1','system_member',1],['pB','SYS2','system_member',1]])
            write_tsv(ann/'args.tsv',['plasmid_id','arg'],[[p,'blaX'] for p in ['pA','pB']])
            write_tsv(ann/'mge.tsv',['plasmid_id','kind','label'],[[p,'IS','IS1'] for p in ['pA','pB']])
            write_tsv(ann/'mobility.tsv',['plasmid_id','mobility'],[])
            write_tsv(ann/'amrfinder_elements.tsv',['plasmid_id','gene','element_type'],[]);(ann/'status.json').write_text(json.dumps({'amrfinder_status':'measured'}))
            module_fields=['module_id','plasmid_id','mge_signature','boundary_truncated']
            write_tsv(ann/'mobile_module_candidates.tsv',module_fields,[[module,p,'IS:IS1',0] for p in ['pA','pB']])
            write_tsv(m/'quality.tsv',['mag_id','taxonomy','eligible'],[['magA','s__hostA',1],['magB','s__hostB',1]])
            write_tsv(m/'mag_abundance.tsv',['mag_id','sample_id','breadth','coverage'],[[mag,sample,int((mag,sample) in [('magA','S1'),('magB','S2')]),5] for mag in ['magA','magB'] for sample in ['S1','S2']])
            write_tsv(host/'stratum.host_edges.tsv',['plasmid_id','mag_id','stratum_id','correlation','q_value'],[['pA',mag,'stratum',.9,.01] for mag in ['magA','magB']])
            (host/'status.json').write_text(json.dumps({'cohorts':[{'stratum_id':'stratum','sample_ids':['S1','S2']}]}))
            md=d/'metadata';write_tsv(md,['sample_id','group'],[['S1','A'],['S2','B']])
            ab=d/'abundance';write_tsv(ab,['plasmid_id','sample_id','breadth','coverage','raw_count','tpm'],[[p,sample,0 if (p,sample)==('pB','S1') else 1,2,5,100] for p in ['pA','pB'] for sample in ['S1','S2']])
            settings=d/'settings';settings.write_text('{}')
            positive=d/'positive';delivery.deliver(c,s,ann,ab,m,md,[host],[],[],[],settings,positive,.75,.99999,10000)
            self.assertEqual({r['pattern'] for r in cat.rows(positive/'dissemination_candidates.tsv')},{'B','C'})
            self.assertEqual(len(cat.rows(positive/'ARG_module_sharing.tsv')),1)
            # Different MAG IDs without classified host differences, and an
            # ARG window without MGE context, must not create B or C evidence.
            write_tsv(m/'quality.tsv',['mag_id','taxonomy','eligible'],[['magA','unknown',1],['magB','unknown',1]])
            write_tsv(ann/'mobile_module_candidates.tsv',module_fields,[[module,'pA','',0],[module,'pB','IS:IS1',0]])
            negative=d/'negative';delivery.deliver(c,s,ann,ab,m,md,[host],[],[],[],settings,negative,.75,.99999,10000)
            self.assertEqual({r['pattern'] for r in cat.rows(negative/'dissemination_candidates.tsv')},{'D'})

    @unittest.skipUnless(importlib.util.find_spec('weasyprint'),'weasyprint is required for native delivery tests')
    def test_real_pdf_manifest_and_unknown_host_risk_are_explicit(self):
        import protocol_delivery as delivery
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);c=d/'catalogue';c.mkdir();s=d/'systems';s.mkdir();ann=d/'ann';ann.mkdir();m=d/'mags';m.mkdir()
            cat.fasta(c/'plasmids.fasta',[('p','ACGT'*250)])
            write_tsv(c/'structure.tsv',['plasmid_id','structure_grade','completeness'],[['p','fragment_or_unknown','not_established']])
            write_tsv(c/'candidate_evidence.tsv',['feature_id','sample_id','identity_grade'],[['p','S1','plasmid_like_contig'],['p','S2','plasmid_like_contig']])
            write_tsv(c/'features.tsv',['feature_id','length_bp'],[['p',1000]])
            write_tsv(s/'membership.tsv',['plasmid_id','system_id','membership_grade'],[['p','','unassigned']])
            write_tsv(ann/'args.tsv',['plasmid_id','arg'],[['p','blaX']]);write_tsv(ann/'mge.tsv',['plasmid_id','kind','label'],[]);write_tsv(ann/'mobility.tsv',['plasmid_id','mobility'],[])
            write_tsv(ann/'amrfinder_elements.tsv',['plasmid_id','gene','element_type'],[['p','virX','VIRULENCE'],['p','stressX','STRESS']])
            (ann/'status.json').write_text(json.dumps({'amrfinder_status':'measured'}))
            write_tsv(ann/'mobile_module_candidates.tsv',['module_id','plasmid_id','mge_signature','boundary_truncated'],[])
            write_tsv(m/'quality.tsv',['mag_id','taxonomy','eligible'],[]);write_tsv(m/'mag_abundance.tsv',['mag_id','sample_id','breadth','coverage'],[])
            md=d/'metadata';write_tsv(md,['sample_id','group','site','environment'],[['S1','A','X','water'],['S2','B','Y','soil']])
            ab=d/'abundance';write_tsv(ab,['plasmid_id','sample_id','breadth','coverage','raw_count','tpm'],[['p','S1',1,1,5,10],['p','S2',1,1,7,20]])
            settings=d/'settings';settings.write_text('{}')
            execution=d/'execution.json';execution.write_text(json.dumps([
                {'kind':'evidence','producer':'AMRFINDERPLUS','output':'versions_amrfinderplus','evidence':['AMRFINDERPLUS','amrfinderplus','4.2.7']},
                {'kind':'evidence','producer':'AMRFINDERPLUS','output':'database_identity','evidence':['amrfinderplus_db',{'algorithm':'sha256-files','sha256':'a'*64,'file_count':1,'bytes':50}]}]))
            audit=d/'input_audit';audit.mkdir()
            write_tsv(audit/'checksums.tsv',['sample_id','mate','path','sha256','pairs'],[['S1',1,'R1.fastq','a'*64,2],['S1',2,'R2.fastq','b'*64,2]])
            write_tsv(audit/'seqkit_stats.tsv',['file','num_seqs','sum_len'],[['R1.fastq',2,200],['R2.fastq',2,200]])
            out=d/'delivery';delivery.deliver(c,s,ann,ab,m,md,[],[],[],[audit],settings,out,.75,.99999,10000,execution_records=execution)
            self.assertTrue((out/'final_report.pdf').read_bytes().startswith(b'%PDF'))
            manifest={r['path'] for r in cat.rows(out/'workflow_manifest.tsv')}
            self.assertIn('final_report.pdf',manifest);self.assertIn('final_report.html',manifest)
            self.assertIn('software_manifest.tsv',manifest);self.assertEqual(cat.rows(out/'software_manifest.tsv')[0]['version_value'],'4.2.7')
            self.assertEqual(cat.rows(out/'database_manifest.tsv')[0]['sha256'],'a'*64)
            self.assertEqual(len(cat.rows(out/'checksums.txt')),2)
            self.assertEqual({r['sample_id'] for r in cat.rows(out/'raw_read_stats.tsv')},{'S1'})
            self.assertEqual(cat.rows(out/'samplesheet.tsv'),cat.rows(md))
            risk=cat.rows(out/'risk_profile.tsv')[0];self.assertEqual(risk['host_evidence_types'],'unknown');self.assertEqual(risk['genetic_hazard_ARG'],'blaX');self.assertEqual(risk['detected_samples'],'2')
            self.assertEqual(risk['genetic_hazard_virulence'],'virX');self.assertEqual(risk['stress_genes'],'stressX')
            self.assertEqual(risk['virulence_status'],'catalogued_gene_candidate_detected')
            environment=cat.rows(out/'environment_gene_summary.tsv');self.assertEqual({r['environment'] for r in environment},{'water','soil'})
            self.assertTrue(all(r['detected_samples']=='1' for r in environment))
            metadata=cat.rows(out/'plasmid_metadata.tsv');self.assertEqual(len(metadata),1)
            self.assertEqual(metadata[0]['plasmid_id'],'p');self.assertEqual(metadata[0]['source_samples'],'S1|S2')
            self.assertEqual(metadata[0]['sequence_status'],'plasmid_like_contig');self.assertEqual(metadata[0]['virulence_candidates'],'virX')
            events=cat.rows(out/'dissemination_candidates.tsv');self.assertEqual([r['pattern'] for r in events],['D']);self.assertEqual(events[0]['confidence'],'insufficient')
            # A near-strain observation only supports an A candidate when an
            # eligible system and a host edge in this same stratum are present.
            write_tsv(s/'membership.tsv',['plasmid_id','system_id','membership_grade','eligible_for_abundance'],[['p','system1','system_member',1]])
            write_tsv(m/'quality.tsv',['mag_id','taxonomy','eligible'],[['mag1','s__host',1]])
            write_tsv(m/'mag_abundance.tsv',['mag_id','sample_id','breadth','coverage'],[['mag1','S1',1,5],['mag1','S2',1,5]])
            host=d/'x.host_edges.tsv';write_tsv(host,['plasmid_id','mag_id','stratum_id','correlation','q_value'],[['p','mag1','stratum1',.9,.01]])
            strata=d/'matrices';strata.mkdir();(strata/'status.json').write_text(json.dumps({'cohorts':[{'stratum_id':'stratum1','sample_ids':['S1','S2']}]}))
            strain=d/'strain';strain.mkdir();write_tsv(strain/'sample_identity.tsv',['sample_id','bam_name'],[['S1','S1.shared.bam'],['S2','S2.shared.bam']])
            write_tsv(strain/'run_genomeWide_compare.tsv',['name1','name2','genome','popANI','coverage_overlap','compared_bases_count'],[['S1.shared.bam','S2.shared.bam','M:mag1',.999999,.9,20000]])
            positive=d/'candidateA';delivery.deliver(c,s,ann,ab,m,md,[host,strata],[strain],[],[],settings,positive,.75,.99999,10000)
            self.assertEqual(cat.rows(positive/'dissemination_candidates.tsv')[0]['pattern'],'A')
            # An association estimated in another stratum must not be applied here.
            (strata/'status.json').write_text(json.dumps({'cohorts':[{'stratum_id':'stratum1','sample_ids':['otherA','otherB']}]}))
            negative=d/'notA';delivery.deliver(c,s,ann,ab,m,md,[host,strata],[strain],[],[],settings,negative,.75,.99999,10000)
            self.assertEqual(cat.rows(negative/'dissemination_candidates.tsv')[0]['pattern'],'D')
