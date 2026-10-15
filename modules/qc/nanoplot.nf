/*
 * NanoPlot quality report for ONT long reads (DAG node: qc_nanoplot; mandatory
 * on ont/hybrid when long reads are available). The report directory is
 * renamed with the sample id so the static publishDir stays unambiguous.
 */
process NANOPLOT {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/qc_long.yml"

    publishDir "${params.outdir}/01_qc/nanoplot", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(long_reads)

    output:
    tuple val(meta), path("${meta.id}.nanoplot_out", type: 'dir'), emit: report_dir
    path "${meta.id}.nanoplot_out/NanoPlot-report.html", emit: html, optional: true

    script:
    """
    NanoPlot --fastq ${long_reads} --outdir ${meta.id}.nanoplot_out --threads ${task.cpus}
    """
}
