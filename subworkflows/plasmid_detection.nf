/*
 * Shared plasmid detection subworkflow: geNomad via the nf-core
 * genomad/endtoend module (mandatory) + optional PLASMe/PlasX/Platon/SCAPP,
 * followed by consensus integration (DAG node plasmid_consensus) and
 * structure detection (plasmid_structure).
 */
include { GENOMAD_ENDTOEND as GENOMAD } from '../modules/nf-core/genomad/endtoend/main'
include { PLASME } from '../modules/detection/plasme'
include { PLASX } from '../modules/detection/plasx'
include { PLATON } from '../modules/detection/platon'
include { SCAPP_DETECT } from '../modules/detection/scapp'
include { PLASMID_CONSENSUS } from '../modules/detection/consensus'
include { PLASMID_STRUCTURE } from '../modules/detection/structure'

workflow PLASMID_DETECTION {
    take:
    ch_assembly    // tuple(meta, fasta)
    ch_scapp_reads // tuple(meta, graph, r1, r2); empty unless SCAPP can run

    main:
    // nf-core module expects the database as tuple val(meta2), path(db); the
    // db carries no sample metadata, so meta2 is an empty map.
    GENOMAD(ch_assembly, Channel.value([[:], file(params.genomad_db, checkIfExists: true)]))

    ch_plasme = Channel.empty()
    if (params.plasmid_detection_tools.contains('plasme')) {
        PLASME(ch_assembly, Channel.value(file(params.plasme_db, checkIfExists: true)))
        ch_plasme = PLASME.out.predictions
    }
    ch_plasx = Channel.empty()
    if (params.plasmid_detection_tools.contains('plasx')) {
        PLASX(ch_assembly,
              Channel.value(file(params.plasx_annotations, checkIfExists: true)),
              Channel.value(file(params.plasx_model, checkIfExists: true)))
        ch_plasx = PLASX.out.predictions
    }
    ch_platon = Channel.empty()
    if (params.plasmid_detection_tools.contains('platon')) {
        PLATON(ch_assembly, Channel.value(file(params.platon_db, checkIfExists: true)))
        ch_platon = PLATON.out.predictions
    }
    ch_scapp = Channel.empty()
    if (params.plasmid_detection_tools.contains('scapp')) {
        SCAPP_DETECT(ch_scapp_reads)
        ch_scapp = SCAPP_DETECT.out.predictions
    }

    // Merge per-sample: missing optional tools become null and are dropped
    // from the extras list, so disabled tools never block the consensus.
    ch_consensus_in = GENOMAD.out.plasmid_summary
        .join(ch_assembly)
        .join(ch_plasme, remainder: true)
        .join(ch_plasx, remainder: true)
        .join(ch_platon, remainder: true)
        .join(ch_scapp, remainder: true)
        .map { meta, summary, assembly, plasme, plasx, platon, scapp ->
            def extras = [plasme, plasx, platon, scapp].findAll { it != null }
            tuple(meta, assembly, summary, extras)
        }

    PLASMID_CONSENSUS(ch_consensus_in)
    PLASMID_STRUCTURE(PLASMID_CONSENSUS.out.contigs)

    emit:
    plasmid_contigs = PLASMID_CONSENSUS.out.contigs
    predictions     = PLASMID_CONSENSUS.out.predictions
    consensus       = PLASMID_CONSENSUS.out.consensus
    structure       = PLASMID_STRUCTURE.out.structure
}
