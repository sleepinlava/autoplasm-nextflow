/*
 * FastQC on raw or cleaned short reads (DAG nodes: qc_fastqc_raw / qc_fastqc_clean;
 * optional, enabled by params.run_fastqc).
 */
process FASTQC {
    tag { "${meta.id}.${stage}" }
    label 'process_low'
    conda "${projectDir}/envs/qc_short.yml"

    publishDir "${params.outdir}/01_qc/${meta.id}/fastqc_${stage}", mode: params.publish_dir_mode

    input:
    tuple val(meta), val(stage), path(read1), path(read2)

    output:
    tuple val(meta), path("*.zip"), path("*.html"), emit: results

    script:
    """
    fastqc --threads ${task.cpus} --extract --outdir . ${read1} ${read2}
    """
}
