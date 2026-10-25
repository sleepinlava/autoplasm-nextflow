// Same-run metaSPAdes FASTG/k provenance + original minigut Illumina pairs.
// This fixture certifies the execution/input contract, not biological recall.
nextflow.enable.dsl = 2

include { MINIGUT_FASTG } from './spades_minigut_fastg'
include { RECYCLER_INPUTS } from '../../../modules/binning/recycler_inputs'
include { RECYCLER } from '../../../modules/binning/recycler'

workflow {
    def root = params.test_data
    def r1 = file("${root}/test_data/test_minigut_R1.fastq.gz", checkIfExists: true)
    def r2 = file("${root}/test_data/test_minigut_R2.fastq.gz", checkIfExists: true)

    ch_reads = Channel.of([[id: 'minigut'], r1, r2])
    MINIGUT_FASTG(ch_reads)
    RECYCLER_INPUTS(MINIGUT_FASTG.out.recycler_graph.join(ch_reads,
        failOnDuplicate: true, failOnMismatch: true))
    RECYCLER(RECYCLER_INPUTS.out.bam, Channel.value(tuple(file("${moduleDir}/../../../bin/validate_recycler_inputs.py", checkIfExists: true), file("${moduleDir}/../../../bin/run_recycler_checked.py", checkIfExists: true))))
}
