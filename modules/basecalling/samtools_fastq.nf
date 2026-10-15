/*
 * samtools fastq: convert long-read BAM to FASTQ (DAG node: long_read_bam_to_fastq).
 */
process SAMTOOLS_FASTQ {
    tag { meta.id }
    label 'process_low'
    conda "${projectDir}/envs/basecalling.yml"

    publishDir "${params.outdir}/00_input_validation/basecalling/${meta.id}", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(bam)

    output:
    tuple val(meta), path("${meta.id}.bam.fastq"), emit: long_reads

    script:
    """
    samtools fastq -@ ${task.cpus} -o ${meta.id}.bam.fastq ${bam}
    """
}
