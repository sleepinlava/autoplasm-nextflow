/*
 * Host prediction subworkflow (DAG category host_prediction, 07): MetaPhlAn4
 * (default) on cleaned reads, Kraken2 (optional, illumina only),
 * PlasmidHostFinder (assembly platform, on plasmid contigs).
 */
include { METAPHLAN } from '../modules/host/metaphlan'
include { KRAKEN2 } from '../modules/host/kraken2'
include { PLASMIDHOSTFINDER } from '../modules/host/plasmidhostfinder'

workflow HOST_PROFILE_READS {
    take:
    ch_short_reads
    ch_long_reads

    main:
    ch_short_in = ch_short_reads.map { meta, r1, r2 -> tuple(meta, [r1, r2]) }
    ch_reads = ch_short_in.mix(ch_long_reads)

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
            Channel.value(file(params.metaphlan_db, checkIfExists: true))
        )
        ch_host_profile = METAPHLAN.out.profile
    }
    if (params.host_prediction_tools.contains('kraken2') && is_illumina) {
        KRAKEN2(ch_short_reads, Channel.value(file(params.kraken2_db, checkIfExists: true)))
    }
    if (params.host_prediction_tools.contains('plasmidhostfinder') && is_assembly) {
        PLASMIDHOSTFINDER(ch_plasmids, Channel.value(file(params.plasmidhostfinder_db, checkIfExists: true)))
    }

    emit:
    host_profile = ch_host_profile  // tuple(meta, metaphlan tsv); may be empty
}
