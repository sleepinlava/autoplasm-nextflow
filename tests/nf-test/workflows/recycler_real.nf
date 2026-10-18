// Real metaSPAdes assembly graph + real illumina BAM feeding RECYCLER.
// Data: pinned nf-core/test-datasets minigut assembly and illumina pair
// (AUTOPLASM_TEST_DATA). Scaffolding: SPADES (--meta, w2spades profile)
// builds the fastg graph; bowtie2 aligns the same reads to the real minigut
// assembly for a genuine BAM. RECYCLER now takes tuple(meta, graph, bam).
nextflow.enable.dsl = 2

include { MINIGUT_FASTG } from './spades_minigut_fastg'
include { RECYCLER } from '../../../modules/binning/recycler'

process ALIGN_FOR_RECYCLER {
    label 'process_low'
    container 'community.wave.seqera.io/library/bowtie2_htslib_samtools_pigz:edeb13799090a2a6'

    input:
    tuple val(meta), path(ref), path(r1), path(r2)

    output:
    tuple val(meta), path("${meta.id}.bam"), emit: bam

    script:
    """
    bowtie2-build --quiet ${ref} ref_idx
    bowtie2 --quiet -x ref_idx -1 ${r1} -2 ${r2} -p ${task.cpus} \\
        | samtools sort -@ ${task.cpus} -o ${meta.id}.bam
    samtools index ${meta.id}.bam
    """
}

workflow {
    def root = params.test_data
    def assembly = file("${root}/minigut.fasta", checkIfExists: true)
    def r1 = file("${root}/test_data/test_minigut_R1.fastq.gz", checkIfExists: true)
    def r2 = file("${root}/test_data/test_minigut_R2.fastq.gz", checkIfExists: true)

    MINIGUT_FASTG(Channel.of([[id: 'minigut'], r1, r2]))
    ALIGN_FOR_RECYCLER(Channel.of([[id: 'minigut'], assembly, r1, r2]))
    RECYCLER(MINIGUT_FASTG.out.fastg.join(ALIGN_FOR_RECYCLER.out.bam))
}
