/*
 * Host-plasmid linking subworkflow (DAG category host_plasmid_linking;
 * default disabled — params.host_plasmid_linking). Methods: co_abundance
 * (cross-sample), sequence (per-sample), CRISPR (currently rejected),
 * long_read (per-sample bridge evidence).
 */
include { LINK_COABUNDANCE } from '../modules/linking/coabundance'
include { MERGE_ABUNDANCE as MERGE_ABUNDANCE_FOR_LINK } from '../modules/cross_sample/merge_abundance'
include { LINK_SEQUENCE } from '../modules/linking/sequence'
include { LINK_LONGREAD } from '../modules/linking/longread'

workflow HOST_LINKING {
    take:
    ch_plasmids          // tuple(meta, fasta)
    ch_assembly          // tuple(meta, fasta)
    ch_longread_bam      // tuple(meta, long-read-only bam)
    ch_plasmid_abundance // tuple(meta, coverm tsv)
    ch_host_profile      // tuple(meta, metaphlan tsv); may be empty
    ch_mag_bins          // tuple(meta, dir); may be empty
    ch_taxonomy          // tuple(meta, tsv); may be empty
    has_long_reads       // val boolean

    main:
    ch_links = Channel.empty()

    if (params.host_plasmid_linking) {
        if (params.host_linking_optional_methods.contains('crispr')) {
            throw new IllegalArgumentException(
                'CRISPR host-plasmid linking is not implemented; remove crispr from host_linking_optional_methods'
            )
        }
        // co_abundance: cross-sample over collected per-sample tables
        if (params.host_linking_methods.contains('co_abundance')) {
            ch_abundance_input = ch_plasmid_abundance.toList().map { entries ->
                tuple(entries.collect { entry -> entry[0].id }, entries.collect { entry -> entry[1] })
            }
            ch_profile_input = ch_host_profile.toList().map { entries ->
                tuple(entries.collect { entry -> entry[0].id }, entries.collect { entry -> entry[1] })
            }
            MERGE_ABUNDANCE_FOR_LINK(
                ch_abundance_input,
                'coabundance_plasmid_abundance',
                'plasmid_id'
            )
            LINK_COABUNDANCE(MERGE_ABUNDANCE_FOR_LINK.out.table, ch_profile_input)
            ch_links = ch_links.mix(LINK_COABUNDANCE.out.links)
        }
        // sequence similarity: needs MAG bins
        if (params.host_linking_methods.contains('sequence')) {
            ch_seq_in = ch_plasmids
                .map { meta, contigs -> tuple(meta, [contigs]) }
                .join(ch_mag_bins, remainder: true)
                .filter { meta, payload, bins -> payload != null }
                .map { meta, payload, bins -> tuple(meta, [payload[0], bins ?: []]) }
                .join(ch_taxonomy, remainder: true)
                .filter { meta, payload, tax -> payload != null }
                .map { meta, payload, tax -> tuple(meta, payload[0], payload[1], tax ?: []) }
            LINK_SEQUENCE(ch_seq_in)
            ch_links = ch_links.mix(LINK_SEQUENCE.out.links.map { meta, f -> f })
        }
        // long-read bridge evidence
        if (params.host_linking_methods.contains('long_read') && has_long_reads) {
            LINK_LONGREAD(ch_plasmids.join(ch_assembly).join(ch_longread_bam))
            ch_links = ch_links.mix(LINK_LONGREAD.out.links.map { meta, f -> f })
        }
    }

    emit:
    links = ch_links
}
