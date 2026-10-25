include { reportEvidence; reportSamples } from '../lib/report_events'
include { selectedTools } from '../lib/tool_selection'

/*
 * Shared plasmid detection subworkflow: geNomad via the nf-core
 * genomad/endtoend module (mandatory) + optional PLASMe/PlasX/Platon,
 * followed by consensus integration (pipeline step plasmid_consensus) and
 * structure detection (plasmid_structure).
 */
include { GENOMAD_ENDTOEND as GENOMAD } from '../modules/nf-core/genomad/endtoend/main'
include { PLASME } from '../modules/detection/plasme'
include { PLASX_ANNOTATE; PLASX } from '../modules/detection/plasx'
include { PLATON } from '../modules/detection/platon'
include { PLASMID_CONSENSUS } from '../modules/detection/consensus'
include { PLASMID_STRUCTURE } from '../modules/detection/structure'

workflow PLASMID_DETECTION {
    take:
    ch_assembly    // tuple(meta, fasta)

    main:
    ch_report_events = Channel.empty()
    // nf-core module expects the database as tuple val(meta2), path(db); the
    // db carries no sample metadata, so meta2 is an empty map.
    GENOMAD(ch_assembly, Channel.value([[:], file(params.genomad_db, checkIfExists: true)]))
    ch_report_events = ch_report_events.mix(reportEvidence([channels: GENOMAD.out], '04_plasmid_detection', 'GENOMAD'))

    ch_plasme = Channel.empty()
    if (selectedTools(params.plasmid_detection_tools).contains('plasme')) {
        PLASME(ch_assembly, Channel.value(file(params.plasme_db, checkIfExists: true)),
               Channel.value(file(params.plasme_dir, checkIfExists: true)), Channel.value(tuple(file("${moduleDir}/../bin/normalize_plasme_outputs.py", checkIfExists: true), file("${moduleDir}/../bin/plasme_runtime.py", checkIfExists: true))))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: PLASME.out], '04_plasmid_detection', 'PLASME'))
        ch_plasme = PLASME.out.predictions
    }
    ch_plasx = Channel.empty()
    if (selectedTools(params.plasmid_detection_tools).contains('plasx')) {
        // Numbered dependency staging avoids basename collisions in full source
        // trees. Recursive regular files make reference/source bytes cache inputs.
        def resource = { location -> Channel.value(tuple(file(location, checkIfExists: true),
            files("${location}/**", type: 'file', hidden: true))) }
        PLASX_ANNOTATE(ch_assembly, resource.call(params.plasx_anvio_source),
                      resource.call(params.plasx_cog_db), resource.call(params.plasx_pfam_db), Channel.value(tuple(file("${moduleDir}/../bin/plasx_inputs.py", checkIfExists: true), file("${moduleDir}/../bin/anvio_checked.py", checkIfExists: true))))
        PLASX(PLASX_ANNOTATE.out.annotations, resource.call(params.plasx_source), resource.call(params.plasx_profiles),
              Channel.value(file(params.plasx_model, checkIfExists: true)), Channel.value(tuple(file("${moduleDir}/../bin/plasx_inputs.py", checkIfExists: true), file("${moduleDir}/../bin/plasx_checked.py", checkIfExists: true))))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: PLASX_ANNOTATE.out], '04_plasmid_detection', 'PLASX_ANNOTATE'))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: PLASX.out], '04_plasmid_detection', 'PLASX'))
        ch_plasx = PLASX.out.predictions
    }
    ch_platon = Channel.empty()
    if (selectedTools(params.plasmid_detection_tools).contains('platon')) {
        PLATON(ch_assembly, Channel.value(tuple(file(params.platon_db, checkIfExists: true),
            files("${params.platon_db}/**", type: 'file', hidden: true))), Channel.value(file("${moduleDir}/../bin/platon_checked.py", checkIfExists: true)))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: PLATON.out], '04_plasmid_detection', 'PLATON'))
        ch_platon = PLATON.out.predictions
    }

    // Merge per-sample: missing optional tools become null and are dropped
    // from the extras list, so disabled tools never block the consensus.
    ch_consensus_in = GENOMAD.out.plasmid_summary
        .join(ch_assembly)
        .join(ch_plasme, remainder: true)
        .join(ch_plasx, remainder: true)
        .join(ch_platon, remainder: true)
        .map { meta, summary, assembly, plasme, plasx, platon ->
            def extras = [plasme, plasx, platon].findAll { it != null }
            tuple(meta, assembly, summary, extras)
        }

    PLASMID_CONSENSUS(ch_consensus_in)
    ch_report_events = ch_report_events.mix(reportEvidence([channels: PLASMID_CONSENSUS.out], '04_plasmid_detection', 'PLASMID_CONSENSUS'))
    PLASMID_STRUCTURE(PLASMID_CONSENSUS.out.contigs)
    ch_report_events = ch_report_events.mix(reportEvidence([channels: PLASMID_STRUCTURE.out], '04_plasmid_detection', 'PLASMID_STRUCTURE'))

    ch_report_events = ch_report_events.mix(
        reportSamples(PLASMID_CONSENSUS.out.contigs, 'plasmid_fasta', 'PLASMID_CONSENSUS'),
        reportSamples(PLASMID_CONSENSUS.out.consensus, 'consensus', 'PLASMID_CONSENSUS'),
        reportSamples(PLASMID_STRUCTURE.out.structure, 'structure', 'PLASMID_STRUCTURE'))

    emit:
    report_events = ch_report_events
    plasmid_contigs = PLASMID_CONSENSUS.out.contigs
    predictions     = PLASMID_CONSENSUS.out.predictions
    consensus       = PLASMID_CONSENSUS.out.consensus
    structure       = PLASMID_STRUCTURE.out.structure
    aggregated_classification = GENOMAD.out.aggregated_classification
}
