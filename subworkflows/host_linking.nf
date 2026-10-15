/*
 * Host-plasmid linking subworkflow (DAG category host_plasmid_linking;
 * default disabled — params.host_plasmid_linking). Methods: co_abundance
 * (cross-sample), sequence (per-sample), crispr (optional, minced),
 * long_read (per-sample bridge evidence).
 */
include { LINK_COABUNDANCE } from '../modules/linking/coabundance'
include { LINK_SEQUENCE } from '../modules/linking/sequence'
include { LINK_CRISPR } from '../modules/linking/crispr'
include { LINK_LONGREAD } from '../modules/linking/longread'

workflow HOST_LINKING {
    take:
    ch_plasmids          // tuple(meta, fasta)
    ch_assembly          // tuple(meta, fasta)
    ch_contig_bam        // tuple(meta, bam)
    ch_plasmid_abundance // tuple(meta, coverm tsv)
    ch_host_profile      // tuple(meta, metaphlan tsv); may be empty
    ch_mag_bins          // tuple(meta, dir); may be empty
    ch_taxonomy          // tuple(meta, tsv); may be empty
    has_long_reads       // val boolean

    main:
    ch_links = Channel.empty()

    if (params.host_plasmid_linking) {
        // co_abundance: cross-sample over collected per-sample tables
        if (params.host_linking_methods.contains('co_abundance')) {
            ch_abund_files = ch_plasmid_abundance.map { meta, f -> f }.collect()
            ch_prof_files = ch_host_profile.map { meta, f -> f }.collect()
            LINK_COABUNDANCE(ch_abund_files, ch_prof_files)
            ch_links = ch_links.mix(LINK_COABUNDANCE.out.links)
        }
        // sequence similarity: needs MAG bins
        if (params.host_linking_methods.contains('sequence')) {
            ch_seq_in = ch_plasmids
                .join(ch_mag_bins, remainder: true)
                .join(ch_taxonomy, remainder: true)
                .map { meta, contigs, bins, tax ->
                    tuple(meta, contigs,
                          bins ?: [],
                          tax ?: [])
                }
            LINK_SEQUENCE(ch_seq_in)
            ch_links = ch_links.mix(LINK_SEQUENCE.out.links.map { meta, f -> f })
        }
        // CRISPR spacer matching: needs MAG bins
        if (params.host_linking_optional_methods.contains('crispr')) {
            LINK_CRISPR(ch_plasmids.join(ch_mag_bins))
            ch_links = ch_links.mix(LINK_CRISPR.out.links.map { meta, f -> f })
        }
        // long-read bridge evidence
        if (params.host_linking_methods.contains('long_read') && has_long_reads) {
            LINK_LONGREAD(ch_plasmids.join(ch_assembly).join(ch_contig_bam))
            ch_links = ch_links.mix(LINK_LONGREAD.out.links.map { meta, f -> f })
        }
    }

    emit:
    links = ch_links
}
