#!/usr/bin/env python3
"""Assemble evidence-graded protocol results, candidate patterns, and a multidimensional risk profile."""
import argparse
from collections import defaultdict
import csv
import hashlib
import html
import itertools
import json
from pathlib import Path
import shutil
from protocol_catalogue import rows
from build_shared_catalogue import write_tsv,file_digest


def deliver(catalogue,systems,annotations,abundance,mags,metadata,host_results,strain_results,evolution,extras,settings,output,min_breadth,strain_ani,min_compared_bases,min_depth=1.0,execution_records=None):
    output.mkdir();md={r['sample_id']:r for r in rows(metadata)}
    measurements=rows(abundance);detected=defaultdict(set)
    for r in measurements:
        if float(r['breadth'])>=min_breadth and float(r['coverage'])>=min_depth:detected[r['plasmid_id']].add(r['sample_id'])
    members=rows(systems/'membership.tsv');system_plasmids=defaultdict(set);plasmid_system=defaultdict(set)
    for r in members:
        if r['system_id'] and r['membership_grade']=='system_member' and r.get('eligible_for_abundance')=='1':
            system_plasmids[r['system_id']].add(r['plasmid_id']);plasmid_system[r['plasmid_id']].add(r['system_id'])
    host=[]
    stratum_samples={}
    for root in host_results:
        if root.is_dir() and (root/'status.json').exists():
            for cohort in json.loads((root/'status.json').read_text()).get('cohorts',[]):
                stratum_samples[cohort['stratum_id']]=set(cohort['sample_ids'])
    mag_tax={r['mag_id']:r['taxonomy'] for r in rows(mags/'quality.tsv') if r['eligible']=='1'}
    for root in host_results:
        candidates=list(root.rglob('host_evidence.tsv')) if root.is_dir() else []
        for path in candidates:
            for r in rows(path):host.append([r['plasmid_id'],'','',r['host_taxonomy'],'reference_homology',r['reference_id']])
        candidates=list(root.rglob('host_range.tsv')) if root.is_dir() else []
        for path in candidates:
            for r in rows(path):
                for genus in r['predicted_genera'].split('|'):
                    if genus:host.append([r['plasmid_id'],'','',genus,'model_prediction','MOSTPLAS'])
        candidates=list(root.rglob('*.host_edges.tsv')) if root.is_dir() else ([root] if root.name.endswith('.host_edges.tsv') else [])
        mag_tax={r['mag_id']:r['taxonomy'] for r in rows(mags/'quality.tsv') if r['eligible']=='1'}
        for path in candidates:
            for r in rows(path):host.append([r['plasmid_id'],r['mag_id'],r['stratum_id'],mag_tax.get(r['mag_id'],'unknown'),'coabundance_association',f"r={r['correlation']};q={r['q_value']}"])
    write_tsv(output/'host_evidence.tsv',['plasmid_id','mag_id','stratum_id','host_taxonomy','evidence_grade','support'],host)
    mag_detected=defaultdict(set)
    for r in rows(mags/'mag_abundance.tsv'):
        if float(r['breadth'])>=min_breadth and float(r['coverage'])>=min_depth:mag_detected[r['mag_id']].add(r['sample_id'])
    host_by_sample=defaultdict(set)
    for p,mag,stratum,tax,grade,support in host:
        if mag:
            for sample in mag_detected[mag]&detected[p]&stratum_samples.get(stratum,set()):host_by_sample[p,sample].add(mag)
    strains=[]
    strain_names={r['bam_name']:r['sample_id'] for folder in strain_results for p in folder.rglob('sample_identity.tsv') for r in rows(p)}
    for folder in strain_results:
        for path in folder.rglob('*genomeWide_compare.tsv'):
            for r in rows(path):
                r['sample_id_a']=strain_names[r['name1']]
                r['sample_id_b']=strain_names[r['name2']]
                strains.append(r)
    if strains:write_tsv(output/'strain_comparison.tsv',list(strains[0]),([r[k] for k in strains[0]] for r in strains))
    else:write_tsv(output/'strain_comparison.tsv',['name1','name2','genome','popANI','coverage_overlap','compared_bases_count'],[])
    close=set()
    for r in strains:
        # inStrain reports BAM names; sample_identity.tsv supplies stable IDs.
        if r['genome'].startswith('M:') and float(r['popANI'])>=strain_ani and float(r['coverage_overlap'])>=min_breadth and int(r['compared_bases_count'])>=min_compared_bases:
            close.add((r['genome'][2:],*sorted([r['sample_id_a'],r['sample_id_b']])))
    events=[]
    for system,ps in sorted(system_plasmids.items()):
        samples=sorted(set.union(*(detected[p] for p in ps)))
        for a,b in itertools.combinations(samples,2):
            ma=set.union(*(host_by_sample[p,a] for p in ps));mb=set.union(*(host_by_sample[p,b] for p in ps))
            strain_support=sorted(m for m in ma&mb if (m,a,b) in close)
            if strain_support:
                pattern='A';support='same_system;near_strain_unique_MAG_loci='+','.join(strain_support);counter='MAG/locus comparison may omit genomic differences; host link is statistical; clone and plasmid are not physically linked'
            elif ma and mb and (ta:={mag_tax[m] for m in ma if mag_tax.get(m,'unknown')!='unknown'}) and (tb:={mag_tax[m] for m in mb if mag_tax.get(m,'unknown')!='unknown'}) and ta.isdisjoint(tb):
                pattern='B';support='same_system;different_associated_MAG_candidates';counter='different MAG IDs alone do not establish different biological hosts; no physical linkage'
            else:
                pattern='D';support='system_codetection';counter='strain or sample-specific host support insufficient'
            events.append([system,a,b,pattern,support,counter,'common_source|unsampled_host|assembly_error|database_bias','low',md[a].get('collection_date',''),md[b].get('collection_date',''),md[a].get('site',''),md[b].get('site','')])
    # Unassigned shared sequences are still observations, not system evidence.
    for p,samples in sorted(detected.items()):
        if not plasmid_system[p]:
            for a,b in itertools.combinations(sorted(samples),2):events.append([p,a,b,'D','representative_codetection','no_eligible_whole_plasmid_system_or_physical_host_link','common_source|assembly_error','insufficient',md[a].get('collection_date',''),md[b].get('collection_date',''),md[a].get('site',''),md[b].get('site','')])
    module_groups=defaultdict(list)
    for r in rows(annotations/'mobile_module_candidates.tsv'):
        if r['mge_signature']:module_groups[r['module_id']].append(r)
    sharing=[]
    for module,items in sorted(module_groups.items()):
        for a,b in itertools.combinations(items,2):
            pa,pb=a['plasmid_id'],b['plasmid_id']
            if pa==pb or not plasmid_system[pa] or not plasmid_system[pb] or not plasmid_system[pa].isdisjoint(plasmid_system[pb]):continue
            sharing.append([module,pa,pb,'exact_ARG_window_sequence',a['boundary_truncated'],b['boundary_truncated']])
            for sa,sb in itertools.product(sorted(detected[pa]),sorted(detected[pb])):
                if sa==sb:continue
                sa,sb=sorted([sa,sb])
                events.append([module,sa,sb,'C','exact_shared_ARG_MGE_window_in_distinct_systems',
                    'window is not a validated mobile unit; boundary truncation='+a['boundary_truncated']+'|'+b['boundary_truncated'],
                    'common_ancestry|recombination|assembly_error','low',md[sa].get('collection_date',''),md[sb].get('collection_date',''),md[sa].get('site',''),md[sb].get('site','')])
    write_tsv(output/'ARG_module_sharing.tsv',['module_id','plasmid_a','plasmid_b','evidence','boundary_truncated_a','boundary_truncated_b'],sharing)
    events=sorted(set(tuple(row) for row in events))
    fields=['entity_id','sample_a','sample_b','pattern','supporting_evidence','counterevidence','alternative_explanations','confidence','date_a','date_b','site_a','site_b']
    write_tsv(output/'dissemination_candidates.tsv',fields,events)
    write_tsv(output/'event_evidence_matrix.tsv',fields,events)
    arg_by_plasmid=defaultdict(set);mge_by_plasmid=defaultdict(set);mob={r['plasmid_id']:r['mobility'] for r in rows(annotations/'mobility.tsv')}
    for r in rows(annotations/'args.tsv'):arg_by_plasmid[r['plasmid_id']].add(r['arg'])
    for r in rows(annotations/'mge.tsv'):mge_by_plasmid[r['plasmid_id']].add(r['kind']+':'+r['label'])
    gene_elements=rows(annotations/'amrfinder_elements.tsv')
    screened=json.loads((annotations/'status.json').read_text())['amrfinder_status']=='measured'
    typed_genes=defaultdict(set);environment_genes=defaultdict(lambda: [set(),set()])
    for r in gene_elements:
        p=r['plasmid_id'];typed_genes[p,r['element_type']].add(r['gene'])
        for sample in detected[p]:
            key=(md[sample].get('environment','unknown'),r['element_type'],r['gene'])
            environment_genes[key][0].add(p);environment_genes[key][1].add(sample)
    write_tsv(output/'environment_gene_summary.tsv',['environment','element_type','gene','detected_plasmids','detected_samples'],
        ([*key,len(ps),len(samples)] for key,(ps,samples) in sorted(environment_genes.items())))
    risks=[]
    for r in rows(catalogue/'structure.tsv'):
        p=r['plasmid_id'];samples=sorted(detected[p]);exposure=sorted({md[s].get('environment','unknown') for s in samples})
        virulence=typed_genes[p,'VIRULENCE'];stress=typed_genes[p,'STRESS']
        virulence_status=('catalogued_gene_candidate_detected' if virulence else 'no_catalogued_hit') if screened else 'virulence_not_assessed'
        risks.append([p,'|'.join(sorted(arg_by_plasmid[p])),virulence_status,'|'.join(sorted(virulence)),'|'.join(sorted(stress)),mob.get(p,'not_assessed'),'|'.join(sorted(mge_by_plasmid[p])),
            len(samples),'|'.join(sorted({h[4] for h in host if h[0]==p})) or 'unknown','|'.join(exposure),r['structure_grade'],r['completeness'],'no_uncalibrated_composite_score'])
    write_tsv(output/'risk_profile.tsv',['plasmid_id','genetic_hazard_ARG','virulence_status','genetic_hazard_virulence','stress_genes','mobility_potential','MGE_evidence','detected_samples','host_evidence_types','exposure_context','structure_grade','completeness','score_policy'],risks)
    for source,name in [(catalogue/'plasmids.fasta','final_plasmid_catalog.fa'),(abundance,'plasmid_coverage.tsv')]:shutil.copyfile(source,output/name)
    ids=sorted(detected.keys() | {r['plasmid_id'] for r in rows(catalogue/'structure.tsv')})
    samples=sorted(md)
    by_pair={(r['plasmid_id'],r['sample_id']):r for r in measurements}
    provenance=defaultdict(list);assignments=defaultdict(set);membership_grades=defaultdict(set)
    for r in rows(catalogue/'candidate_evidence.tsv'):provenance[r['feature_id']].append(r)
    for r in members:
        if r['system_id']:assignments[r['plasmid_id']].add(r['system_id'])
        membership_grades[r['plasmid_id']].add(r['membership_grade'])
    lengths={r['feature_id']:r['length_bp'] for r in rows(catalogue/'features.tsv')}
    plasmid_metadata=[]
    for r in rows(catalogue/'structure.tsv'):
        p=r['plasmid_id'];sources=provenance[p];grades={s['identity_grade'] for s in sources}
        state='near_complete_candidate' if r['completeness'] in ('independently_supported','predicted_near_complete') else 'plasmid_like_contig' if 'plasmid_like_contig' in grades else 'unresolved_fragment'
        plasmid_metadata.append([p,lengths[p],state,'|'.join(sorted(grades)),r['structure_grade'],r['completeness'],
            '|'.join(sorted(assignments[p])),'|'.join(sorted(membership_grades[p])),
            '|'.join(sorted({s['sample_id'] for s in sources})),len(detected[p]),len(samples),len(detected[p])/len(samples),
            '|'.join(sorted(arg_by_plasmid[p])),'|'.join(sorted(typed_genes[p,'VIRULENCE'])),'|'.join(sorted(typed_genes[p,'STRESS'])),
            mob.get(p,'not_assessed'),'|'.join(sorted({h[4] for h in host if h[0]==p})) or 'unknown'])
    write_tsv(output/'plasmid_metadata.tsv',['plasmid_id','length_bp','sequence_status','identity_confidence','assembly_confidence','completeness',
        'plasmid_system_id','system_membership_grade','source_samples','detected_samples','total_samples','prevalence','ARG','virulence_candidates','stress_candidates','mobility','host_evidence_type'],plasmid_metadata)
    for field,name in [('raw_count','plasmid_abundance_matrix.tsv'),('tpm','plasmid_tpm_matrix.tsv')]:
        write_tsv(output/name,['plasmid_id']+samples,([fid]+[by_pair[fid,sample][field] for sample in samples] for fid in ids))
    write_tsv(output/'plasmid_prevalence.tsv',['plasmid_id','detected_samples','total_samples','prevalence','interpretation'],
        ([fid,len(detected[fid]),len(samples),len(detected[fid])/len(samples),'fragment_detection_not_whole_plasmid_presence' if not plasmid_system[fid] else 'system_member_detection'] for fid in ids))
    for source,name in [(catalogue,'catalogue'),(systems,'systems'),(annotations,'annotations'),(mags,'mags')]:shutil.copytree(source,output/name)
    shutil.copyfile(metadata,output/'samples.tsv');shutil.copyfile(settings,output/'params.json')
    shutil.copyfile(metadata,output/'samplesheet.tsv');shutil.copyfile(metadata,output/'metadata.tsv')
    checksums=[];raw_stats=[];raw_fields=['file','num_seqs','sum_len']
    for source in extras:
        if source.is_dir() and (source/'checksums.tsv').is_file():
            sample_checksums=rows(source/'checksums.tsv');checksums.extend(sample_checksums)
            statistics=rows(source/'seqkit_stats.tsv')
            if statistics:
                raw_fields=list(statistics[0])
                raw_stats.extend(dict(sample_id=sample_checksums[0]['sample_id'],**r) for r in statistics)
    write_tsv(output/'checksums.txt',['sample_id','mate','path','sha256','pairs'],([r[k] for k in ['sample_id','mate','path','sha256','pairs']] for r in checksums))
    write_tsv(output/'raw_read_stats.tsv',['sample_id']+raw_fields,([r['sample_id']]+[r[k] for k in raw_fields] for r in raw_stats))
    records=json.loads(execution_records.read_text()) if execution_records else []
    (output/'execution_records.json').write_text(json.dumps(records,indent=2)+'\n')
    versions=[]
    resource_records=[]
    declared_settings=json.loads(settings.read_text())
    for r in records:
        if r['kind']=='runtime_command':
            versions.append([r['producer'],r['task_process'],r['runtime_probe']['stdout'],r['runtime_probe']['command'],'runtime_probe',r['script_sha256']])
        elif r.get('output','').startswith('versions_') and isinstance(r['evidence'],list):
            task,tool,version=r['evidence']
            versions.append([tool,task,version,'',r['output'],''])
        elif r.get('output') in ('database_identity','source_identity'):
            resource,identity=r['evidence']
            resource_records.append([resource,r['producer'],declared_settings.get(resource,''),identity.get('resource_state','captured'),
                *[identity.get(k,'') for k in ['algorithm','sha256','file_count','bytes']]])
    write_tsv(output/'database_manifest.tsv',['resource','producer','declared_path','resource_state','identity_algorithm','sha256','files','bytes'],resource_records)
    evidence=output/'execution_evidence';evidence.mkdir()
    for i,source in enumerate(sorted([*host_results,*strain_results,*evolution,*extras],key=lambda p:(p.name,str(p)))):
        name=f'{i:04d}_{source.name}'
        if source.is_dir():shutil.copytree(source,evidence/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        else:shutil.copyfile(source,evidence/name)
    for root in [output/'systems',evidence]:
        for p in sorted(root.rglob('*.mapping_stats.json')):
            versions.append(['pysam','',json.loads(p.read_text())['pysam_version'],'','artifact:'+str(p.relative_to(output)),''])
        for p in sorted(root.rglob('*r_package_versions.tsv')):
            for r in rows(p):versions.append([r['Package'],'',r['Version'],'','artifact:'+str(p.relative_to(output)),''])
        for p in sorted(root.rglob('version*.txt')):
            if any(part.endswith('source_snapshot') for part in p.relative_to(output).parts):continue
            versions.append([p.parent.name,'',p.read_text(),'','artifact:'+str(p.relative_to(output)),''])
        for p in sorted(root.rglob('status.json')):
            if any(part.endswith('source_snapshot') for part in p.relative_to(output).parts):continue
            for tool,version in json.loads(p.read_text()).get('versions',{}).items():
                versions.append([tool,'',version,'','artifact:'+str(p.relative_to(output)),''])
    write_tsv(output/'software_manifest.tsv',['tool','task_process','version_value','probe_command','version_source','script_sha256'],versions)
    policy='Observations, model predictions, statistical associations and mechanistic hypotheses are distinct. A–D are candidate patterns; no direct transfer, direction or time is established. Completeness is not inferred from bin membership. No benchmark was run.'
    body=f'<h1>Short-read plasmidome protocol report</h1><p>{html.escape(policy)}</p><p>Catalogue representatives: {len(risks)}; samples: {len(md)}; candidate events: {len(events)}.</p>'
    for title,path in [('Risk profile','risk_profile.tsv'),('Host evidence','host_evidence.tsv'),('Candidate patterns','dissemination_candidates.tsv')]:
        table=rows(output/path);body+=f'<h2>{title}</h2>'
        if table:
            body+='<table><thead><tr>'+''.join('<th>'+html.escape(k)+'</th>' for k in table[0])+'</tr></thead><tbody>'
            for r in table[:100]:body+='<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in r.values())+'</tr>'
            body+='</tbody></table><p>Full data are in '+path+'.</p>'
        else:body+='<p>No eligible results; inspect execution evidence status files.</p>'
    document='<!doctype html><html><head><meta charset="utf-8"><style>@page { size:A3 landscape; margin:15mm } body{font:12px sans-serif} table{border-collapse:collapse;table-layout:fixed;width:100%;font-size:8px} td,th{border:1px solid #bbb;padding:4px;overflow-wrap:anywhere}</style></head><body>'+body+'</body></html>'
    (output/'final_report.html').write_text(document)
    from weasyprint import HTML
    HTML(string=document,base_url=str(output)).write_pdf(output/'final_report.pdf')

    manifest=[]
    for p in sorted(output.rglob('*')):
        if p.is_file():manifest.append([str(p.relative_to(output)),p.stat().st_size,file_digest(p)])
    write_tsv(output/'workflow_manifest.tsv',['path','bytes','sha256'],manifest)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['catalogue','systems','annotations','abundance','mags','metadata','settings','output']:p.add_argument('--'+k,type=Path,required=True)
 for k in ['host-results','strain-results','evolution','extras']:p.add_argument('--'+k,type=Path,nargs='*',default=[])
 p.add_argument('--min-breadth',type=float,default=.75);p.add_argument('--strain-ani',type=float,default=.99999);p.add_argument('--min-compared-bases',type=int,default=10000)
 p.add_argument('--min-depth',type=float,default=1.0)
 p.add_argument('--execution-records',type=Path)
 deliver(**vars(p.parse_args()))
