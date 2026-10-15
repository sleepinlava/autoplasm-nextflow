/*
 * NanoPlot quality report for ONT long reads (DAG node: qc_nanoplot; mandatory
 * on ont/hybrid when long reads are available).
 */
process NANOPLOT {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/qc_long.yml"

    publishDir "${params.outdir}/01_qc/${meta.id}/nanoplot", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(long_reads)

    output:
    tuple val(meta), path("*"), emit: report_dir
    path "*NanoPlot-report.html", emit: html, optional: true

    script:
    """
    NanoPlot --fastq ${long_reads} --outdir . --threads ${task.cpus}
    """
}
