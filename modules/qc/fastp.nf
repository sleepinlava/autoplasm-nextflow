/*
 * fastp adapter trimming + quality filtering (DAG node: qc_fastp; mandatory
 * for illumina and hybrid platforms).
 */
process FASTP {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/qc_short.yml"

    publishDir "${params.outdir}/01_qc/fastp", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(read1), path(read2)

    output:
    tuple val(meta), path("${meta.id}_R1.clean.fastq.gz"), path("${meta.id}_R2.clean.fastq.gz"), emit: reads
    tuple val(meta), path("${meta.id}.fastp.html"), emit: html
    tuple val(meta), path("${meta.id}.fastp.json"), emit: json

    script:
    """
    fastp \\
        -i ${read1} -I ${read2} \\
        -o ${meta.id}_R1.clean.fastq.gz -O ${meta.id}_R2.clean.fastq.gz \\
        --thread ${task.cpus} \\
        --html ${meta.id}.fastp.html \\
        --json ${meta.id}.fastp.json
    """
}
