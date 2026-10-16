/*
 * Cross-sample subworkflow: merged abundance tables (tables/), diversity and
 * differential abundance (11), FastSpar co-occurrence network (12), and the
 * final report. Sample-count gates mirror config_default.yaml thresholds.
 */
include { MERGE_ABUNDANCE; MERGE_ABUNDANCE as MERGE_ABUNDANCE_PLASMID } from '../modules/cross_sample/merge_abundance'
include { DIVERSITY } from '../modules/cross_sample/diversity'
include { DIFFERENTIAL_ABUNDANCE } from '../modules/cross_sample/differential'
include { DESEQ2 } from '../modules/cross_sample/deseq2'
include { NETWORK_PREPARE } from '../modules/cross_sample/network_prepare'
include { FASTSPAR } from '../modules/cross_sample/fastspar'
include { REPORT } from '../modules/cross_sample/report'

workflow CROSS_SAMPLE {
    take:
    ch_contig_tables    // tuple(meta, coverm tsv); empty on assembly platform
    ch_plasmid_tables   // tuple(meta, coverm tsv); empty on assembly platform
    ch_plasmids         // tuple(meta, fasta) — report/catalog trigger
    ch_done             // channel of trigger items from all optional branches
    n_samples           // val: number of samples in the samplesheet
    n_groups            // val: number of distinct groups

    main:
    ch_metadata = Channel.value(file(params.samplesheet, checkIfExists: true))
    ch_stats_done = Channel.empty()

    if (params.platform != 'assembly') {
        ch_contig_inputs = ch_contig_tables.toList().map { entries ->
            tuple(entries.collect { entry -> entry[0].id }, entries.collect { entry -> entry[1] })
        }
        ch_plasmid_inputs = ch_plasmid_tables.toList().map { entries ->
            tuple(entries.collect { entry -> entry[0].id }, entries.collect { entry -> entry[1] })
        }

        // merged contig coverage (diversity / differential input)
        MERGE_ABUNDANCE(
            ch_contig_inputs,
            'contig_abundance',
            'contig_id'
        )
        ch_contig_merged = MERGE_ABUNDANCE.out.table
        ch_stats_done = ch_stats_done.mix(ch_contig_merged)

        // merged plasmid abundance (DESeq2 / network input; plasmid_id column)
        MERGE_ABUNDANCE_PLASMID(
            ch_plasmid_inputs,
            'plasmid_abundance',
            'plasmid_id'
        )
        ch_plasmid_merged = MERGE_ABUNDANCE_PLASMID.out.table
        ch_stats_done = ch_stats_done.mix(ch_plasmid_merged)

        if (params.run_diversity && n_samples >= params.min_diversity_samples) {
            DIVERSITY(ch_contig_merged, ch_metadata)
            ch_stats_done = ch_stats_done.mix(DIVERSITY.out.metrics, DIVERSITY.out.beta)
        }
        if (params.run_differential_internal && n_groups >= 2) {
            DIFFERENTIAL_ABUNDANCE(ch_contig_merged, ch_metadata)
            ch_stats_done = ch_stats_done.mix(DIFFERENTIAL_ABUNDANCE.out.results)
        }
        if (params.run_differential_deseq2 && n_groups >= 2) {
            DESEQ2(ch_plasmid_merged, ch_metadata)
            ch_stats_done = ch_stats_done.mix(DESEQ2.out.results)
        }
        if (params.run_network && n_samples >= params.network_min_samples) {
            NETWORK_PREPARE(ch_plasmid_merged)
            FASTSPAR(NETWORK_PREPARE.out.network_input)
            ch_stats_done = ch_stats_done.mix(FASTSPAR.out.correlation, FASTSPAR.out.covariance)
        }
    }

    // Wait for platform outputs and the enabled cross-sample analyses.
    // publishDir is asynchronous; completion alone is not a publication barrier.
    ch_report_trigger = ch_done.mix(ch_plasmids.map { meta, f -> f }, ch_stats_done).collect()
    REPORT(ch_report_trigger)
}
