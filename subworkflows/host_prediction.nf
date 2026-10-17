/*
 * Host prediction subworkflow (DAG category host_prediction, 07): MetaPhlAn4
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
    ch_host_profile = Channel.empty()
    if (params.host_prediction_tools.contains('metaphlan') && !is_assembly) {
        HOST_PROFILE_READS(ch_short_reads, ch_long_reads)
        METAPHLAN(
            HOST_PROFILE_READS.out.reads,
            Channel.value(file(params.metaphlan_db, checkIfExists: true)),
            false   // save_samfile
        )
        ch_host_profile = METAPHLAN.out.profile
    }
    if (params.host_prediction_tools.contains('kraken2') && is_illumina) {
        KRAKEN2(
            ch_short_reads.map { meta, r1, r2 -> tuple(meta + [single_end: false], [r1, r2]) },
            Channel.value(file(params.kraken2_db, checkIfExists: true)),
            false,  // save_output_fastqs
            false   // save_reads_assignment
        )
    }
    if (params.host_prediction_tools.contains('plasmidhostfinder') && is_assembly) {
        PLASMIDHOSTFINDER(ch_plasmids, Channel.value(file(params.plasmidhostfinder_db, checkIfExists: true)))
    }

    emit:
    host_profile = ch_host_profile  // tuple(meta, metaphlan profile txt); may be empty
}
