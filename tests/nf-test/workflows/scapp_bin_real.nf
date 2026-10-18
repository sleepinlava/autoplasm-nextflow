// Real metaSPAdes assembly graph feeding SCAPP_BIN.
// Same scaffolding as scapp_detect_real.nf: genuine minigut fastg graph
// (SPADES --meta via w2spades profile) mined by SCAPP with the same real
// illumina pair — the production graph contract (illumina.nf).
nextflow.enable.dsl = 2

include { MINIGUT_FASTG } from './spades_minigut_fastg'
include { SCAPP_BIN } from '../../../modules/binning/scapp_bin'

workflow {
    def root = params.test_data
    def r1 = file("${root}/test_data/test_minigut_R1.fastq.gz", checkIfExists: true)
    def r2 = file("${root}/test_data/test_minigut_R2.fastq.gz", checkIfExists: true)

    MINIGUT_FASTG(Channel.of([[id: 'minigut'], r1, r2]))
    SCAPP_BIN(MINIGUT_FASTG.out.fastg.combine(Channel.of([r1, r2])))
}
