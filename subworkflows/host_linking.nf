include { resourceInput } from '../lib/resource_inputs'
include { reportEvidence; reportSamples } from '../lib/report_events'
include { selectedTools } from '../lib/tool_selection'

/*
 * Host-plasmid linking subworkflow (stage 07 host_plasmid_linking;
 * default disabled — params.host_plasmid_linking). Methods: co_abundance
 * (cross-sample), sequence (per-sample), CRISPR (currently rejected),
 * long_read (per-sample bridge evidence), HOTSPOT (optional Transformer
 * host prediction, needs --hotspot_home/--hotspot_db/--hotspot_models).
 */
include { LINK_COABUNDANCE } from '../modules/linking/coabundance'
include { LINK_SEQUENCE } from '../modules/linking/sequence'
include { LINK_LONGREAD } from '../modules/linking/longread'
include { LINK_HOTSPOT } from '../modules/linking/hotspot'

workflow HOST_LINKING {
    take:
    ch_plasmids          // tuple(meta, fasta)
    ch_assembly          // tuple(meta, fasta)
    ch_longread_bam      // tuple(meta, long-read-only bam)
    ch_plasmid_abundance // path(shared-reference plasmid long table)
    ch_host_profile      // tuple(meta, metaphlan tsv); may be empty
    ch_mag_bins          // tuple(meta, dir); may be empty
    ch_taxonomy          // tuple(meta, tsv); may be empty
    has_long_reads       // val boolean

    main:
    ch_report_events = Channel.empty()
    ch_links = Channel.empty()
    ch_sequence_scores = Channel.empty()

    if (params.host_plasmid_linking) {
        if (selectedTools(params.host_linking_optional_methods).contains('crispr')) {
            throw new IllegalArgumentException(
                'CRISPR host-plasmid linking is not implemented; remove crispr from host_linking_optional_methods'
            )
        }
        // co_abundance: shared sequence features, all measured samples retained
        if (selectedTools(params.host_linking_methods).contains('co_abundance')) {
            ch_profile_input = ch_host_profile.toList().map { entries ->
                tuple(entries.collect { entry -> entry[0].id }, entries.collect { entry -> entry[1] })
            }
            LINK_COABUNDANCE(ch_plasmid_abundance, ch_profile_input)
            ch_report_events = ch_report_events.mix(reportEvidence([channels: LINK_COABUNDANCE.out], '07_host_prediction', 'LINK_COABUNDANCE'))
            ch_links = ch_links.mix(LINK_COABUNDANCE.out.links)
        }
        // Sequence composition scores only; failed calibration disables host links.
        if (selectedTools(params.host_linking_methods).contains('sequence')) {
            ch_seq_in = ch_plasmids
                .map { meta, contigs -> tuple(meta, [contigs]) }
                .join(ch_mag_bins, remainder: true, failOnDuplicate: true)
                .filter { meta, payload, bins -> payload != null }
                .map { meta, payload, bins -> tuple(meta, [payload[0], bins ?: []]) }
                .join(ch_taxonomy, remainder: true, failOnDuplicate: true)
                .filter { meta, payload, tax -> payload != null }
                .map { meta, payload, tax -> tuple(meta, payload[0], payload[1], tax ?: []) }
            LINK_SEQUENCE(ch_seq_in)
            ch_report_events = ch_report_events.mix(reportEvidence([channels: LINK_SEQUENCE.out], '07_host_prediction', 'LINK_SEQUENCE'))
            ch_sequence_scores = LINK_SEQUENCE.out.scores
        }
        // long-read bridge evidence
        if (selectedTools(params.host_linking_methods).contains('long_read') && has_long_reads) {
            LINK_LONGREAD(ch_plasmids.join(ch_assembly).join(ch_longread_bam))
            ch_report_events = ch_report_events.mix(reportEvidence([channels: LINK_LONGREAD.out], '07_host_prediction', 'LINK_LONGREAD'))
            ch_links = ch_links.mix(LINK_LONGREAD.out.links.map { meta, f -> f })
        }
        // HOTSPOT Transformer host prediction (optional; needs --hotspot_home/--hotspot_db/--hotspot_models)
        if (selectedTools(params.host_linking_optional_methods).contains('hotspot')) {
            LINK_HOTSPOT(ch_plasmids,
                Channel.value(['preprocessing.py', 'hotspot.py', 'model.py'].collect { name ->
                    file("${params.hotspot_home}/${name}", checkIfExists: true)
                }),
                Channel.value(resourceInput(params.hotspot_db)),
                Channel.value(resourceInput(params.hotspot_models)), Channel.value(tuple(file("${moduleDir}/../bin/convert_hotspot_lineage.py", checkIfExists: true), file("${moduleDir}/../bin/hotspot_runtime.py", checkIfExists: true))))
            ch_report_events = ch_report_events.mix(reportEvidence([channels: LINK_HOTSPOT.out], '07_host_prediction', 'LINK_HOTSPOT'))
            ch_links = ch_links.mix(LINK_HOTSPOT.out.links.map { meta, f -> f })
        }
    }

    emit:
    report_events = ch_report_events
    links = ch_links
    sequence_scores = ch_sequence_scores
}
