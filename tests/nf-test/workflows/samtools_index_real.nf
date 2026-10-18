// Real BAM indexing with SAMTOOLS_INDEX (custom bridge module, no container
// declared in modules/mag/samtools_index.nf — the container is pinned by the
// w2mag profile in tests/nf-test/nextflow.config, see nodes-mag-samtools-index
// suite). Scaffolding reproduces the real coverage alignment: bowtie2 maps
// the minigut illumina pair to the real minigut assembly.
nextflow.enable.dsl = 2

include { SAMTOOLS_INDEX } from '../../../modules/mag/samtools_index'

process ALIGN_FOR_INDEX {
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
    """
}

process KEEP_BAI {
    // Test scaffolding: SAMTOOLS_INDEX has no publishDir, so surface the BAI
    // into the test outdir (binary output, copied verbatim).
    publishDir "${params.outdir}/w2_mag", mode: 'copy'

    input:
    tuple val(meta), path(bai)

    output:
    path(bai)

    script:
    """
    true
    """
}

workflow {
    def root = params.test_data
    def assembly = file("${root}/minigut.fasta", checkIfExists: true)
    def r1 = file("${root}/test_data/test_minigut_R1.fastq.gz", checkIfExists: true)
    def r2 = file("${root}/test_data/test_minigut_R2.fastq.gz", checkIfExists: true)

    ALIGN_FOR_INDEX(Channel.of([[id: 'minigut'], assembly, r1, r2]))
    SAMTOOLS_INDEX(ALIGN_FOR_INDEX.out.bam)
    KEEP_BAI(SAMTOOLS_INDEX.out.bai)
}
