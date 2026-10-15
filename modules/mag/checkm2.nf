/*
 * CheckM2 MAG quality assessment (DAG node: mag_checkm2; optional).
 */
process CHECKM2 {
    tag { meta.id }
    label 'process_high'
    conda "${projectDir}/envs/checkm2.yml"

    publishDir "${params.outdir}/07_host_prediction/mag/${meta.id}/checkm2", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(mag_bins)

    output:
    tuple val(meta), path("${meta.id}.checkm2_quality.tsv"), emit: quality_report

    script:
    """
    checkm2 predict --input ${mag_bins} --output-directory checkm2_out \\
        --threads ${task.cpus}
    cp checkm2_out/quality_report.tsv ${meta.id}.checkm2_quality.tsv
    """
}
