include { protocolAssets } from '../lib/protocol_assets'
include { reportEvidence; reportSamples; reportSettings } from '../lib/report_events'
/*
 * Cross-sample subworkflow: merged abundance tables (tables/), diversity and
 * differential abundance (11), FastSpar co-occurrence network (12), and the
 * final report. Sample-count gates are set by the nextflow.config defaults.
 */
include { STATISTICS_INPUTS } from '../modules/cross_sample/statistics_inputs'
include { DIVERSITY } from '../modules/cross_sample/diversity'
include { DIFFERENTIAL_ABUNDANCE } from '../modules/cross_sample/differential'
include { ANCOMBC2 } from '../modules/cross_sample/ancombc2'
include { DESEQ2 } from '../modules/cross_sample/deseq2'
include { NETWORK_PREPARE } from '../modules/cross_sample/network_prepare'
include { FASTSPAR } from '../modules/cross_sample/fastspar'
include { REPORTING } from '../modules/cross_sample/report'

workflow CROSS_SAMPLE {
    take:
    ch_contig_tables    // path(shared contig long table); empty on assembly platform
    ch_plasmid_tables   // path(shared plasmid long table); empty on assembly platform
    ch_quantification_states // producer sample/feature/count state; required for reads platforms
    ch_plasmids         // tuple(meta, fasta) — report/catalog trigger
    ch_done             // channel of trigger items from all optional branches
    n_samples           // val: number of samples in the samplesheet
    n_groups            // val: number of distinct groups

    main:
    ch_report_events = Channel.empty()
    ch_metadata = Channel.value(file(params.samplesheet, checkIfExists: true))
    ch_stats_done = Channel.empty()

    if (params.platform != 'assembly') {
        // Tables already contain all samples on the same sequence reference.
        ch_contig_one = ch_contig_tables.toList().map { files ->
            if (files.size() != 1) error "Expected exactly one shared contig table, received ${files.size()}"
            files[0]
        }
        ch_plasmid_one = ch_plasmid_tables.toList().map { files ->
            if (files.size() != 1) error "Expected exactly one shared plasmid table, received ${files.size()}"
            files[0]
        }
        ch_state_one = ch_quantification_states.toList().map { files ->
            if (files.size() != 1) error "Expected exactly one quantification state table, received ${files.size()}"
            files[0]
        }
        STATISTICS_INPUTS(ch_contig_one, ch_plasmid_one, ch_state_one, ch_metadata, n_samples,
            [file("${moduleDir}/../bin/validate_statistics_inputs.py",checkIfExists:true), file("${moduleDir}/../bin/collect_shared_abundance.py",checkIfExists:true)])
        ch_report_events = ch_report_events.mix(reportEvidence([channels: STATISTICS_INPUTS.out], '11_diversity', 'STATISTICS_INPUTS'))
        ch_contig_merged = STATISTICS_INPUTS.out.contigs
        ch_plasmid_merged = STATISTICS_INPUTS.out.plasmids
        ch_valid_metadata = STATISTICS_INPUTS.out.metadata
        ch_stats_done = ch_stats_done.mix(ch_contig_merged, ch_plasmid_merged)

        if (!params.short_read_protocol && params.run_diversity && n_samples >= params.min_diversity_samples) {
            DIVERSITY(ch_plasmid_merged, ch_valid_metadata, [file("${moduleDir}/../bin/diversity.R",checkIfExists:true), file("${moduleDir}/../bin/statistics_design.R",checkIfExists:true), file("${moduleDir}/../bin/statistics_input_contract.R",checkIfExists:true)])
            ch_report_events = ch_report_events.mix(reportEvidence([channels: DIVERSITY.out], '11_diversity', 'DIVERSITY'))
            ch_stats_done = ch_stats_done.mix(DIVERSITY.out.metrics, DIVERSITY.out.beta)
        }
        if (params.run_differential_internal && n_groups >= 2) {
            DIFFERENTIAL_ABUNDANCE(ch_plasmid_merged, ch_valid_metadata, [file("${moduleDir}/../bin/differential_abundance.R",checkIfExists:true), file("${moduleDir}/../bin/statistics_input_contract.R",checkIfExists:true)])
            ch_report_events = ch_report_events.mix(reportEvidence([channels: DIFFERENTIAL_ABUNDANCE.out], '11_diversity', 'DIFFERENTIAL_ABUNDANCE'))
            ch_stats_done = ch_stats_done.mix(DIFFERENTIAL_ABUNDANCE.out.results)
        }
        if (!params.short_read_protocol && params.run_ancombc2 && n_groups >= 2) {
            ANCOMBC2(ch_plasmid_merged,ch_valid_metadata, protocolAssets("${moduleDir}/../bin",'ancombc2_plasmid.R'))
            ch_report_events = ch_report_events.mix(reportEvidence([channels:ANCOMBC2.out],'11_diversity','ANCOMBC2'))
        }
        if (params.run_differential_deseq2 && n_groups >= 2) {
            DESEQ2(ch_plasmid_merged, ch_valid_metadata, [file("${moduleDir}/../bin/deseq2_plasmid.R",checkIfExists:true), file("${moduleDir}/../bin/statistics_input_contract.R",checkIfExists:true)])
            ch_report_events = ch_report_events.mix(reportEvidence([channels: DESEQ2.out], '11_diversity', 'DESEQ2'))
            ch_stats_done = ch_stats_done.mix(DESEQ2.out.results)
        }
        if (params.run_network && n_samples >= params.network_min_samples) {
            // Preparation records empty/filtered cohorts explicitly. Only a
            // matrix eligible AFTER filtering may enter the estimator.
            NETWORK_PREPARE(ch_plasmid_merged, ch_valid_metadata, [file("${moduleDir}/../bin/network_prepare.R",checkIfExists:true), file("${moduleDir}/../bin/statistics_input_contract.R",checkIfExists:true)])
            ch_report_events = ch_report_events.mix(reportEvidence([channels: NETWORK_PREPARE.out], '12_network', 'NETWORK_PREPARE'))
            FASTSPAR(NETWORK_PREPARE.out.eligible_input)
            ch_report_events = ch_report_events.mix(reportEvidence([channels: FASTSPAR.out], '12_network', 'FASTSPAR'))
            ch_stats_done = ch_stats_done.mix(FASTSPAR.out.correlation, FASTSPAR.out.covariance)
        }
    }

    // Every enabled branch contributes its declared outputs, including late
    // optional tasks. Only explicit detection files are staged for summaries.
    REPORTING(ch_done.mix(ch_report_events), ch_metadata, reportSettings(params))
}
