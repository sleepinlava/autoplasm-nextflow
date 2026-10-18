// Real metaSPAdes assembly graph feeding SCAPP_DETECT.
// Data: pinned nf-core/test-datasets minigut illumina pair
// (AUTOPLASM_TEST_DATA). SPADES (--meta, w2spades profile) assembles the
// pair into a genuine assembly_graph.fastg, then SCAPP mines that graph
// with the same real reads — the same graph contract as production
// (subworkflows/illumina.nf feeds METASPADES.out.fastg to SCAPP).
nextflow.enable.dsl = 2

include { MINIGUT_FASTG } from './spades_minigut_fastg'
include { SCAPP_DETECT } from '../../../modules/detection/scapp'

workflow {
    def root = params.test_data
    def r1 = file("${root}/test_data/test_minigut_R1.fastq.gz", checkIfExists: true)
    def r2 = file("${root}/test_data/test_minigut_R2.fastq.gz", checkIfExists: true)

    MINIGUT_FASTG(Channel.of([[id: 'minigut'], r1, r2]))
    SCAPP_DETECT(MINIGUT_FASTG.out.fastg.combine(Channel.of([r1, r2])))
}
