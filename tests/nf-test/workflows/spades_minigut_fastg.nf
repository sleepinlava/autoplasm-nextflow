// Test scaffolding (not a pipeline node): assemble the real minigut illumina
// pair with the vendored SPADES module (as METASPADES, production-style
// --meta via the w2spades test profile) to obtain a genuine
// assembly_graph.fastg and k provenance for Recycler.
// The fastg emit is a plain (non-gzipped) copy made by the vendored module.
nextflow.enable.dsl = 2

include { SPADES } from '../../../modules/nf-core/spades/main'

workflow MINIGUT_FASTG {
    take:
    reads   // tuple(val(meta), path(r1), path(r2))

    main:
    SPADES(reads.map { meta, r1, r2 -> tuple(meta, [r1, r2], [], []) }, [], [], Channel.value(file("${moduleDir}/../../../bin/spades_graph_provenance.py", checkIfExists: true)))

    emit:
    fastg   = SPADES.out.fastg    // tuple(val(meta), path(fastg))
    recycler_graph = SPADES.out.recycler_graph // tuple(meta, FASTG, actual-k provenance)
    contigs = SPADES.out.contigs  // tuple(val(meta), path(fa.gz))
}
