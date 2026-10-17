/*
 * Assembly platform subworkflow (DAG platform_resolution.assembly): the
 * user-provided assembly FASTA passes through directly (DAG node
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
    ch_assembly = ch_samples

    QUAST(ch_assembly.map { meta, fasta -> tuple(meta, [fasta]) },
        Channel.value([[:], []]), Channel.value([[:], []]))

    PLASMID_DETECTION(ch_assembly, Channel.empty())
    ch_plasmids = PLASMID_DETECTION.out.plasmid_contigs.filter { meta, f -> f.size() > 0 }

    PLASMID_DOWNSTREAM(
        ch_plasmids, Channel.empty(), Channel.empty(),
        Channel.empty(), Channel.empty()
    )

    HOST_PREDICTION(Channel.empty(), Channel.empty(), ch_plasmids, false, true)

    COMPARATIVE(ch_plasmids, PLASMID_DOWNSTREAM.out.bakta_dir)

    emit:
    plasmids       = ch_plasmids
    contig_tables  = Channel.empty()
    plasmid_tables = Channel.empty()
    done = PLASMID_DETECTION.out.consensus.map { meta, f -> f }
        .mix(PLASMID_DETECTION.out.structure.map { meta, f -> f })
        .mix(QUAST.out.tsv.map { meta, f -> f })
}
