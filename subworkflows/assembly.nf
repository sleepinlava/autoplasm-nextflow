include { reportEvidence; reportSamples } from '../lib/report_events'
/*
 * Assembly platform subworkflow (platform: assembly): the
 * user-provided assembly FASTA passes through directly (pipeline step
 * assembly_provided); no read-based steps (QC, coverage, abundance, MAG,
 * linking) are instantiated. Host prediction uses PlasmidHostFinder.
 */
include { QUAST } from '../modules/nf-core/quast/main'
include { PLASMID_DETECTION } from './plasmid_detection'
include { PLASMID_DOWNSTREAM } from './plasmid_downstream'
include { HOST_PREDICTION } from './host_prediction'
include { COMPARATIVE } from './comparative'

workflow ASSEMBLY {
    take:
    ch_samples // tuple(meta, assembly fasta)

    main:
    ch_report_events = Channel.empty()
    ch_assembly = ch_samples

    QUAST(ch_assembly.map { meta, fasta -> tuple(meta, [fasta]) },
        Channel.value([[:], []]), Channel.value([[:], []]))
    ch_report_events = ch_report_events.mix(reportEvidence([channels: QUAST.out], '03_assembly_qc', 'QUAST'))

    PLASMID_DETECTION(ch_assembly)
    ch_report_events = ch_report_events.mix(PLASMID_DETECTION.out.report_events)
    ch_plasmids = PLASMID_DETECTION.out.plasmid_contigs.filter { meta, f -> f.size() > 0 }

    PLASMID_DOWNSTREAM(
        ch_plasmids, Channel.empty(), Channel.empty(),
        Channel.empty(), Channel.empty(), Channel.empty()
    )
    ch_report_events = ch_report_events.mix(PLASMID_DOWNSTREAM.out.report_events)

    HOST_PREDICTION(Channel.empty(), Channel.empty(), ch_plasmids, false, true)
    ch_report_events = ch_report_events.mix(HOST_PREDICTION.out.report_events)

    COMPARATIVE(ch_plasmids, PLASMID_DOWNSTREAM.out.bakta_dir)
    ch_report_events = ch_report_events.mix(COMPARATIVE.out.report_events)

    ch_report_events = ch_report_events.mix(ch_assembly.map { meta, source ->
        tuple([section: '02_assembly', producer: 'assembly_provided', kind: 'provided_input',
               sample_id: meta.id.toString(), evidence: source.toString()], [])
    })

    emit:
    report_events = ch_report_events
    plasmids       = ch_plasmids
    contig_tables  = Channel.empty()
    plasmid_tables = Channel.empty()
    done = ch_report_events
}
