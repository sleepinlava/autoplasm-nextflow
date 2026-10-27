include { resourceInput } from '../lib/resource_inputs'
include { reportEvidence; reportSamples } from '../lib/report_events'
include { selectedTools } from '../lib/tool_selection'

/*
 * Host prediction subworkflow (stage 07 host_prediction): MetaPhlAn4
 * (default) on cleaned reads, Kraken2 (optional, illumina only),
 * PlasmidHostFinder (assembly platform, on plasmid contigs).
 *
 * METAPHLAN / KRAKEN2 are the vendored nf-core modules
 * (metaphlan/metaphlan, kraken2/kraken2) included under their original
 * process names; publishDir and tool arguments for them live in
 * conf/nfcore_host_comparative.config.
 */
include { METAPHLAN_METAPHLAN as METAPHLAN } from '../modules/nf-core/metaphlan/metaphlan'
include { KRAKEN2_KRAKEN2 as KRAKEN2 } from '../modules/nf-core/kraken2/kraken2'
include { PLASMIDHOSTFINDER } from '../modules/host/plasmidhostfinder'

workflow HOST_PROFILE_READS {
    take:
    ch_short_reads
    ch_long_reads

    main:
    // The nf-core modules choose paired-end handling from meta.single_end:
    // short reads are always paired here, long reads always single.
    ch_short_in = ch_short_reads.map { meta, r1, r2 -> tuple(meta + [single_end: false], [r1, r2]) }
    ch_long_in = ch_long_reads.map { meta, fastq -> tuple(meta + [single_end: true], [fastq]) }
    ch_reads = ch_short_in.mix(ch_long_in)

    emit:
    reads = ch_reads
}

workflow HOST_PREDICTION {
    take:
    ch_short_reads  // tuple(meta, r1, r2); empty when unavailable
    ch_long_reads   // tuple(meta, fastq); empty when unavailable
    ch_plasmids     // tuple(meta, fasta); for PlasmidHostFinder
    is_illumina     // val boolean
    is_assembly     // val boolean

    main:
    ch_report_events = Channel.empty()
    ch_host_profile = Channel.empty()
    if (selectedTools(params.host_prediction_tools).contains('metaphlan') && !is_assembly) {
        HOST_PROFILE_READS(ch_short_reads, ch_long_reads)
        METAPHLAN(
            HOST_PROFILE_READS.out.reads,
            Channel.value(resourceInput(params.metaphlan_db)),
            false   // save_samfile
        )
        ch_report_events = ch_report_events.mix(reportEvidence([channels: METAPHLAN.out], '07_host_prediction', 'METAPHLAN'))
        ch_host_profile = METAPHLAN.out.profile
    }
    if (selectedTools(params.host_prediction_tools).contains('kraken2') && is_illumina) {
        KRAKEN2(
            ch_short_reads.map { meta, r1, r2 -> tuple(meta + [single_end: false], [r1, r2]) },
            Channel.value(resourceInput(params.kraken2_db)),
            false,  // save_output_fastqs
            false   // save_reads_assignment
        )
        ch_report_events = ch_report_events.mix(reportEvidence([channels: KRAKEN2.out], '07_host_prediction', 'KRAKEN2'))
    }
    if (selectedTools(params.host_prediction_tools).contains('plasmidhostfinder') && is_assembly) {
        PLASMIDHOSTFINDER(ch_plasmids, Channel.value(resourceInput(params.plasmidhostfinder_db)))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: PLASMIDHOSTFINDER.out], '07_host_prediction', 'PLASMIDHOSTFINDER'))
    }

    emit:
    report_events = ch_report_events
    host_profile = ch_host_profile  // tuple(meta, metaphlan profile txt); may be empty
}
