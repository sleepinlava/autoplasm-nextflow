include { protocolAssets } from '../lib/protocol_assets'
include { reportEvidence; reportSettings } from '../lib/report_events'
include { PROTOCOL_CATALOGUE } from './protocol_catalogue'
include { QUANTIFY_CATALOGUE } from './shared_quantification'
include { PLASMID_DOWNSTREAM } from './plasmid_downstream'
include { MAG_EXTERNAL } from './mag_external'
include { MOBMESS_SYSTEMS; SYSTEM_ABUNDANCE } from '../modules/protocol/systems'
include { MOSTPLAS; PLSDB_SEARCH } from '../modules/protocol/host_models'
include { PROTOCOL_MAG_TABLES; PROTOCOL_HOST_MATRIX; PROTOCOL_HOST_FASTSPAR; PROTOCOL_HOST_EDGES } from '../modules/protocol/mag_association'
include { MMSEQS_EASYCLUSTER as PROTOCOL_PROTEIN_FAMILIES } from '../modules/nf-core/mmseqs/easycluster/main'
include { PROTOCOL_ANNOTATION_PRODUCTS } from '../modules/protocol/annotation'
include { PROTOCOL_FUNCTION_ENRICHMENT } from '../modules/protocol/function_enrichment'
include { PROTOCOL_EVOLUTION } from '../modules/protocol/evolution'
include { PROTOCOL_STRAIN_PROFILE; PROTOCOL_STRAIN_COMPARE } from '../modules/protocol/strain'
include { PROTOCOL_DELIVERY } from '../modules/protocol/delivery'
include { DIVERSITY as SYSTEM_DIVERSITY } from '../modules/cross_sample/diversity'
include { ANCOMBC2 as SYSTEM_ANCOMBC2 } from '../modules/cross_sample/ancombc2'
include { DIVERSITY as PLASMID_DIVERSITY } from '../modules/cross_sample/diversity'
include { ANCOMBC2 as PLASMID_ANCOMBC2 } from '../modules/cross_sample/ancombc2'

workflow SHORT_READ_PROTOCOL {
    take:
    ch_assembly
    ch_reads
    ch_bins
    ch_summary
    ch_structure
    ch_qc_evidence
    ch_upstream_events
    main:
    PROTOCOL_CATALOGUE(ch_assembly, ch_bins, ch_summary, ch_structure)
    ch_catalogue = PROTOCOL_CATALOGUE.out.catalogue.first()
    ch_domain = ch_assembly.map { meta,fasta -> meta.id }.toSortedList().map { [samples:it] }
    ch_plasmids = ch_catalogue.filter { it.resolve('plasmids.fasta').size() > 0 }.combine(ch_domain)
        .map { dir, domain -> tuple([id:'plasmid_catalogue',cohort:true,cohort_samples:domain.samples],dir.resolve('plasmids.fasta')) }
    PLASMID_DOWNSTREAM(ch_plasmids,Channel.empty(),Channel.empty(),Channel.empty(),Channel.empty(),Channel.empty())
    QUANTIFY_CATALOGUE(ch_catalogue,ch_reads,Channel.empty(),'short',ch_domain)
    ch_cellular = ch_bins.map { meta,dir,state -> tuple(meta,dir.resolve('cellular').listFiles().findAll { it.name.endsWith('.fna') }.sort { it.name }) }
        .filter { meta,bins -> bins.size() > 0 }
    MAG_EXTERNAL(ch_cellular)
    ch_report_events = PROTOCOL_CATALOGUE.out.report_events.mix(PLASMID_DOWNSTREAM.out.report_events,
        QUANTIFY_CATALOGUE.out.report_events,MAG_EXTERNAL.out.report_events)
    ch_complete_ids = Channel.value(params.protocol_complete_ids ? file(params.protocol_complete_ids,checkIfExists:true) : [])
    MOBMESS_SYSTEMS(ch_catalogue,ch_complete_ids, protocolAssets("${moduleDir}/../bin",'protocol_systems.py'))
    ch_systems = MOBMESS_SYSTEMS.out.systems.first()
    ch_report_events = ch_report_events.mix(reportEvidence([channels:MOBMESS_SYSTEMS.out],'09_comparative_genomics','MOBMESS_SYSTEMS'))
    SYSTEM_ABUNDANCE(QUANTIFY_CATALOGUE.out.plasmids,ch_systems, protocolAssets("${moduleDir}/../bin",'protocol_systems.py'))
    ch_report_events = ch_report_events.mix(reportEvidence([channels:SYSTEM_ABUNDANCE.out],'10_abundance','SYSTEM_ABUNDANCE'))
    ch_metadata = Channel.value(file(params.samplesheet,checkIfExists:true))
    ch_stat_evidence = Channel.empty()
    if (params.run_diversity) {
        PLASMID_DIVERSITY(QUANTIFY_CATALOGUE.out.plasmids.combine(ch_domain).filter { table,domain -> domain.samples.size() >= params.min_diversity_samples }.map { table,domain -> table },
            ch_metadata,[file("${moduleDir}/../bin/diversity.R"),file("${moduleDir}/../bin/statistics_input_contract.R"),file("${moduleDir}/../bin/statistics_design.R")])
        ch_report_events = ch_report_events.mix(reportEvidence([channels:PLASMID_DIVERSITY.out],'11_diversity','PLASMID_DIVERSITY'))
        ch_stat_evidence = ch_stat_evidence.mix(PLASMID_DIVERSITY.out.inference,PLASMID_DIVERSITY.out.status,PLASMID_DIVERSITY.out.metrics,PLASMID_DIVERSITY.out.beta,PLASMID_DIVERSITY.out.versions_r_packages)
        SYSTEM_DIVERSITY(SYSTEM_ABUNDANCE.out.abundance.combine(ch_domain).filter { table,domain -> domain.samples.size() >= params.min_diversity_samples }.map { table,domain -> table },
            ch_metadata,[file("${moduleDir}/../bin/diversity.R"),file("${moduleDir}/../bin/statistics_input_contract.R"),file("${moduleDir}/../bin/statistics_design.R")])
        ch_report_events = ch_report_events.mix(reportEvidence([channels:SYSTEM_DIVERSITY.out],'11_diversity','SYSTEM_DIVERSITY'))
        ch_stat_evidence = ch_stat_evidence.mix(SYSTEM_DIVERSITY.out.inference,SYSTEM_DIVERSITY.out.status,SYSTEM_DIVERSITY.out.metrics,SYSTEM_DIVERSITY.out.beta,SYSTEM_DIVERSITY.out.versions_r_packages)
    }
    if (params.run_ancombc2) {
        PLASMID_ANCOMBC2(QUANTIFY_CATALOGUE.out.plasmids,ch_metadata,protocolAssets("${moduleDir}/../bin",'ancombc2_plasmid.R'))
        ch_report_events = ch_report_events.mix(reportEvidence([channels:PLASMID_ANCOMBC2.out],'11_diversity','PLASMID_ANCOMBC2'))
        ch_stat_evidence = ch_stat_evidence.mix(PLASMID_ANCOMBC2.out.results)
        SYSTEM_ANCOMBC2(SYSTEM_ABUNDANCE.out.abundance,ch_metadata, protocolAssets("${moduleDir}/../bin",'ancombc2_plasmid.R'))
        ch_report_events = ch_report_events.mix(reportEvidence([channels:SYSTEM_ANCOMBC2.out],'11_diversity','SYSTEM_ANCOMBC2'))
        ch_stat_evidence = ch_stat_evidence.mix(SYSTEM_ANCOMBC2.out.results)
    }
    ch_host = Channel.empty()
    if (params.protocol_host_models) {
        MOSTPLAS(ch_catalogue,ch_complete_ids,Channel.value(file(params.mostplas_source,checkIfExists:true)), protocolAssets("${moduleDir}/../bin",'mostplas_predict.py'))
        PLSDB_SEARCH(ch_catalogue,Channel.value(file(params.plsdb_fasta,checkIfExists:true)),Channel.value(file(params.plsdb_hosts,checkIfExists:true)), protocolAssets("${moduleDir}/../bin",'protocol_hosts.py'))
        ch_host = ch_host.mix(MOSTPLAS.out.predictions,PLSDB_SEARCH.out.predictions)
        ch_report_events = ch_report_events.mix(reportEvidence([channels:MOSTPLAS.out],'07_host_prediction','MOSTPLAS'),
            reportEvidence([channels:PLSDB_SEARCH.out],'07_host_prediction','PLSDB_SEARCH'))
    }
    ch_mag_inputs = ch_bins.filter { meta,dir,state -> dir.resolve('cellular').listFiles().size() > 0 }
        .map { meta,dir,state -> tuple(meta,dir) }
        .join(MAG_EXTERNAL.out.quality).join(MAG_EXTERNAL.out.taxonomy.map { meta,files -> tuple(meta,(files instanceof List ? files[0] : files).parent) })
        .toSortedList { a,b -> a[0].id <=> b[0].id }.map { entries -> tuple(entries.collect { it[0] },entries.collect { it[1] },entries.collect { it[2] },entries.collect { it[3] }) }
    PROTOCOL_MAG_TABLES(ch_mag_inputs,ch_catalogue,QUANTIFY_CATALOGUE.out.contigs, protocolAssets("${moduleDir}/../bin",'protocol_hosts.py'))
    ch_report_events = ch_report_events.mix(reportEvidence([channels:PROTOCOL_MAG_TABLES.out],'07_host_prediction','PROTOCOL_MAG_TABLES'))
    PROTOCOL_HOST_MATRIX(QUANTIFY_CATALOGUE.out.plasmids,PROTOCOL_MAG_TABLES.out.measurements,ch_metadata, protocolAssets("${moduleDir}/../bin",'protocol_hosts.py'))
    ch_host_inputs = PROTOCOL_HOST_MATRIX.out.matrices.flatMap { dir -> dir.listFiles().findAll { it.name.endsWith('.tsv') }.sort { it.name }
        .collect { tuple([id:it.baseName],it) } }
    PROTOCOL_HOST_FASTSPAR(ch_host_inputs)
    PROTOCOL_HOST_EDGES(PROTOCOL_HOST_FASTSPAR.out.association, protocolAssets("${moduleDir}/../bin",'protocol_hosts.py'))
    ch_host = ch_host.mix(PROTOCOL_HOST_EDGES.out.edges,PROTOCOL_HOST_MATRIX.out.matrices)
    ch_report_events = ch_report_events.mix(reportEvidence([channels:PROTOCOL_HOST_MATRIX.out],'07_host_prediction','PROTOCOL_HOST_MATRIX'),
        reportEvidence([channels:PROTOCOL_HOST_FASTSPAR.out],'07_host_prediction','PROTOCOL_HOST_FASTSPAR'),
        reportEvidence([channels:PROTOCOL_HOST_EDGES.out],'07_host_prediction','PROTOCOL_HOST_EDGES'))
    PROTOCOL_PROTEIN_FAMILIES(PLASMID_DOWNSTREAM.out.proteins.filter { meta,faa -> faa.size()>0 })
    ch_report_events = ch_report_events.mix(reportEvidence([channels:PROTOCOL_PROTEIN_FAMILIES.out],'09_comparative_genomics','PROTOCOL_PROTEIN_FAMILIES'))
    PROTOCOL_ANNOTATION_PRODUCTS(ch_catalogue,ch_systems,QUANTIFY_CATALOGUE.out.plasmids,
        PLASMID_DOWNSTREAM.out.genes.map { meta,p -> p }.toList(),PLASMID_DOWNSTREAM.out.args.map { meta,p -> p }.toList(),
        PLASMID_DOWNSTREAM.out.insertion_sequences.map { meta,p -> p }.toList(),PLASMID_DOWNSTREAM.out.integrons.map { meta,files -> files }.flatten().toList(),
        PLASMID_DOWNSTREAM.out.mobility.map { meta,files -> files }.flatten().toList(),
        PLASMID_DOWNSTREAM.out.functional_annotations.map { meta,p -> p }.toList(),PROTOCOL_PROTEIN_FAMILIES.out.tsv.map { meta,p -> p }.toList(), protocolAssets("${moduleDir}/../bin",'protocol_annotation.py'))
    ch_report_events = ch_report_events.mix(reportEvidence([channels:PROTOCOL_ANNOTATION_PRODUCTS.out],'08_annotation','PROTOCOL_ANNOTATION_PRODUCTS'))
    PROTOCOL_FUNCTION_ENRICHMENT(PROTOCOL_ANNOTATION_PRODUCTS.out.products,ch_systems,ch_catalogue, protocolAssets("${moduleDir}/../bin",'protocol_function_enrichment.R'))
    ch_report_events = ch_report_events.mix(reportEvidence([channels:PROTOCOL_FUNCTION_ENRICHMENT.out],'08_annotation','PROTOCOL_FUNCTION_ENRICHMENT'))
    ch_evolution = Channel.empty()
    if (params.protocol_evolution) {
        PROTOCOL_EVOLUTION(PROTOCOL_ANNOTATION_PRODUCTS.out.products,ch_systems,PLASMID_DOWNSTREAM.out.proteins.map { meta,p -> p }.toList(), protocolAssets("${moduleDir}/../bin",'protocol_evolution.py'))
        ch_evolution = PROTOCOL_EVOLUTION.out.evolution
        ch_report_events = ch_report_events.mix(reportEvidence([channels:PROTOCOL_EVOLUTION.out],'09_comparative_genomics','PROTOCOL_EVOLUTION'))
    }
    ch_strain = Channel.empty()
    if (params.protocol_strain) {
        ch_strain_samples = PROTOCOL_MAG_TABLES.out.measurements.flatMap { dir ->
            def eligible_mags = dir.resolve('strain_eligible_mags.tsv').readLines().drop(1).collect { it.split('\t')[0] }.toSet()
            dir.resolve('mag_abundance.tsv').readLines().drop(1).collect { it.split('\t') }
                .findAll { eligible_mags.contains(it[0]) && it[2].toDouble() >= params.protocol_strain_min_coverage && it[3].toDouble() >= params.protocol_min_breadth }
                .collect { it[1] }.unique().sort()
        }
        ch_strain_bams = QUANTIFY_CATALOGUE.out.qualified_bam.map { meta,bam -> tuple(meta.id,meta,bam) }
            .join(ch_strain_samples.map { id -> tuple(id,true) }).map { id,meta,bam,eligible -> tuple(meta,bam) }
        PROTOCOL_STRAIN_PROFILE(ch_strain_bams,ch_catalogue,PROTOCOL_MAG_TABLES.out.measurements, protocolAssets("${moduleDir}/../bin",'protocol_catalogue.py'))
        PROTOCOL_STRAIN_COMPARE(PROTOCOL_STRAIN_PROFILE.out.profile.map { meta,dir -> dir }.toList().filter { it.size()>=2 }, protocolAssets("${moduleDir}/../bin",'protocol_catalogue.py'))
        ch_strain = PROTOCOL_STRAIN_COMPARE.out.comparisons
        ch_report_events = ch_report_events.mix(reportEvidence([channels:PROTOCOL_STRAIN_PROFILE.out],'09_comparative_genomics','PROTOCOL_STRAIN_PROFILE'),
            reportEvidence([channels:PROTOCOL_STRAIN_COMPARE.out],'09_comparative_genomics','PROTOCOL_STRAIN_COMPARE'))
    }
    ch_commands = ch_report_events.filter { record,files -> record.kind == 'runtime_command' || record.output == 'execution_script' }
        .flatMap { record,files -> files }
    PROTOCOL_DELIVERY(ch_catalogue,ch_systems,PROTOCOL_ANNOTATION_PRODUCTS.out.products,QUANTIFY_CATALOGUE.out.plasmids,
        PROTOCOL_MAG_TABLES.out.measurements,ch_metadata,ch_host.toList(),ch_strain.toList(),ch_evolution.toList(),
        ch_qc_evidence.mix(ch_stat_evidence,ch_commands,PROTOCOL_FUNCTION_ENRICHMENT.out.enrichment,PROTOCOL_FUNCTION_ENRICHMENT.out.figures,QUANTIFY_CATALOGUE.out.method,QUANTIFY_CATALOGUE.out.prevalence,QUANTIFY_CATALOGUE.out.mapping_stats).toList(),['bin','envs','modules','subworkflows','lib','conf','assets','main.nf','nextflow.config','modules.json'].collect { file("${moduleDir}/../${it}",checkIfExists:true) },params.collectEntries { k,v -> [(k.toString()):v] },ch_report_events.mix(ch_upstream_events).map { record,files -> record }.toList(), protocolAssets("${moduleDir}/../bin",'protocol_delivery.py'))
    ch_report_events = ch_report_events.mix(reportEvidence([channels:PROTOCOL_DELIVERY.out],'09_comparative_genomics','PROTOCOL_DELIVERY'))
    emit:
    report_events = ch_report_events
    plasmids = ch_plasmids
    contig_tables = QUANTIFY_CATALOGUE.out.contigs
    plasmid_tables = QUANTIFY_CATALOGUE.out.plasmids
    states = QUANTIFY_CATALOGUE.out.states
}
