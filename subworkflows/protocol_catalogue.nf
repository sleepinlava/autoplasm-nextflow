include { protocolAssets } from '../lib/protocol_assets'
include { reportEvidence } from '../lib/report_events'
include { PROTOCOL_CANDIDATES; PROTOCOL_CATALOGUE_PREPARE; PROTOCOL_CATALOGUE_FINALIZE } from '../modules/protocol/catalogue'
include { MMSEQS_EASYCLUSTER as CATALOGUE_CLUSTER_COMPLETE; MMSEQS_EASYCLUSTER as CATALOGUE_CLUSTER_CIRCULAR; MMSEQS_EASYCLUSTER as CATALOGUE_CLUSTER_FRAGMENT } from '../modules/nf-core/mmseqs/easycluster/main'

workflow PROTOCOL_CATALOGUE {
    take:
    ch_assembly
    ch_bins
    ch_summary
    ch_structure
    main:
    ch_inputs = ch_assembly.join(ch_bins.map { meta, dir, state -> tuple(meta, dir) }, failOnDuplicate:true, failOnMismatch:true)
        .join(ch_summary, failOnDuplicate:true, failOnMismatch:true)
        .join(ch_structure, failOnDuplicate:true, failOnMismatch:true)
    PROTOCOL_CANDIDATES(ch_inputs, protocolAssets("${moduleDir}/../bin",'protocol_catalogue.py'))
    ch_sources = ch_assembly.join(PROTOCOL_CANDIDATES.out.candidates, failOnDuplicate:true, failOnMismatch:true)
        .toSortedList { a,b -> a[0].id <=> b[0].id }
        .map { rows -> tuple(rows.collect { it[0].id },rows.collect { it[1] },rows.collect { it[2] }) }
    ch_complete_ids = Channel.value(params.protocol_complete_ids ? file(params.protocol_complete_ids,checkIfExists:true) : [])
    PROTOCOL_CATALOGUE_PREPARE(ch_sources,ch_complete_ids, protocolAssets("${moduleDir}/../bin",'protocol_catalogue.py'))
    CATALOGUE_CLUSTER_COMPLETE(PROTOCOL_CATALOGUE_PREPARE.out.exact.filter { it.resolve('complete.fasta').size() > 0 }
        .combine(ch_sources.map { ids,assemblies,candidates -> [samples:ids] })
        .map { dir,domain -> tuple([id:'complete_catalogue',cohort:true,cohort_samples:domain.samples],dir.resolve('complete.fasta')) })
    CATALOGUE_CLUSTER_CIRCULAR(PROTOCOL_CATALOGUE_PREPARE.out.exact.filter { it.resolve('circular.fasta').size() > 0 }
        .combine(ch_sources.map { ids,assemblies,candidates -> [samples:ids] })
        .map { dir,domain -> tuple([id:'circular_catalogue',cohort:true,cohort_samples:domain.samples],dir.resolve('circular.fasta')) })
    CATALOGUE_CLUSTER_FRAGMENT(PROTOCOL_CATALOGUE_PREPARE.out.exact.filter { it.resolve('fragment.fasta').size() > 0 }
        .combine(ch_sources.map { ids,assemblies,candidates -> [samples:ids] })
        .map { dir,domain -> tuple([id:'fragment_catalogue',cohort:true,cohort_samples:domain.samples],dir.resolve('fragment.fasta')) })
    PROTOCOL_CATALOGUE_FINALIZE(PROTOCOL_CATALOGUE_PREPARE.out.exact,
        CATALOGUE_CLUSTER_COMPLETE.out.tsv.mix(CATALOGUE_CLUSTER_CIRCULAR.out.tsv,CATALOGUE_CLUSTER_FRAGMENT.out.tsv).map { meta,tsv -> tsv }.toList(),
        ch_complete_ids, protocolAssets("${moduleDir}/../bin",'protocol_catalogue.py'))
    emit:
    catalogue = PROTOCOL_CATALOGUE_FINALIZE.out.catalogue
    candidates = PROTOCOL_CANDIDATES.out.candidates
    report_events = reportEvidence([channels:PROTOCOL_CANDIDATES.out],'04_plasmid_detection','PROTOCOL_CANDIDATES')
        .mix(reportEvidence([channels:PROTOCOL_CATALOGUE_PREPARE.out],'09_comparative','PROTOCOL_CATALOGUE_PREPARE'),
             reportEvidence([channels:CATALOGUE_CLUSTER_COMPLETE.out],'09_comparative','CATALOGUE_CLUSTER_COMPLETE'),
             reportEvidence([channels:CATALOGUE_CLUSTER_CIRCULAR.out],'09_comparative','CATALOGUE_CLUSTER_CIRCULAR'),
             reportEvidence([channels:CATALOGUE_CLUSTER_FRAGMENT.out],'09_comparative','CATALOGUE_CLUSTER_FRAGMENT'),
             reportEvidence([channels:PROTOCOL_CATALOGUE_FINALIZE.out],'09_comparative','PROTOCOL_CATALOGUE_FINALIZE'))
}
