/*
 * CONCOCT composition+coverage binning (DAG node: mag_concoct; optional).
 */
process CONCOCT {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/mag.yml"

    publishDir "${params.outdir}/07_host_prediction/mag/${meta.id}/concoct", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly), path(abundance)

    output:
    tuple val(meta), path("concoct_out"), emit: output_dir

    script:
    """
    concoct --composition_file ${assembly} --coverage_file ${abundance} \\
        -o concoct_out -t ${task.cpus}
    """
}
