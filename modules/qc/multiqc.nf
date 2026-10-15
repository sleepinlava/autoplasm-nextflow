/*
 * MultiQC aggregation over QC outputs (DAG nodes: qc_multiqc_illumina /
 * qc_multiqc_ont / qc_multiqc_hifi; optional, enabled by params.run_multiqc).
 */
process MULTIQC {
    tag { label_name }
    label 'process_low'
    conda "${projectDir}/envs/qc_short.yml"

    publishDir "${params.outdir}/01_qc", mode: params.publish_dir_mode

    input:
    path qc_files
    val label_name

    output:
    path "${label_name}_report.html", emit: report

    script:
    """
    multiqc . --outdir . --filename ${label_name}_report.html
    """
}
