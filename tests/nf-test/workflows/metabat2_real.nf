// P3 real-data chain: METABAT2_JGISUMMARIZEBAMCONTIGDEPTHS -> METABAT2 on the
// pinned nf-core/test-datasets metagenome binning fixture (real contigs + real
// sorted BAM + BAI). The vendored metabat2 suite is blocked by a missing
// (unvendored) gunzip setup module; this chain covers the same nodes with real
// data. Backend: podman.
nextflow.enable.dsl = 2

include { METABAT2_JGISUMMARIZEBAMCONTIGDEPTHS } from '../../../modules/nf-core/metabat2/jgisummarizebamcontigdepths/main'
include { METABAT2_METABAT2 as METABAT2 } from '../../../modules/nf-core/metabat2/metabat2/main'

workflow {
    def root = "${params.test_data}/data/genomics/prokaryotes/metagenome/binning/multisample"
    def contigs = file("${root}/contigs.fasta.gz", checkIfExists: true)
    def bam = file("${root}/s1.sorted.bam", checkIfExists: true)
    def bai = file("${root}/s1.sorted.bam.bai", checkIfExists: true)
    def meta = [id: 'binning_s1']
    METABAT2_JGISUMMARIZEBAMCONTIGDEPTHS(tuple(meta, bam, bai))
    METABAT2(METABAT2_JGISUMMARIZEBAMCONTIGDEPTHS.out.depth.map { m, depth -> tuple(m, contigs, depth) })
}
