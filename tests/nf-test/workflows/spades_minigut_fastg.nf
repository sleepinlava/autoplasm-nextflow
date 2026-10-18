// Test scaffolding (not a pipeline node): assemble the real minigut illumina
// pair with the vendored SPADES module (as METASPADES, production-style
// --meta via the w2spades test profile) to obtain a genuine
// assembly_graph.fastg for the SPAdes-graph plasmid tools (scapp/recycler).
// The fastg emit is a plain (non-gzipped) copy made by the vendored module.
nextflow.enable.dsl = 2

include { SPADES } from '../../../modules/nf-core/spades/main'

workflow MINIGUT_FASTG {
    take:
    reads   // tuple(val(meta), path(r1), path(r2))

    main:
    SPADES(reads.map { meta, r1, r2 -> tuple(meta, [r1, r2], [], []) }, [], [])

    emit:
    fastg   = SPADES.out.fastg    // tuple(val(meta), path(fastg))
    contigs = SPADES.out.contigs  // tuple(val(meta), path(fa.gz))
}
