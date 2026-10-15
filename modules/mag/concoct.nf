/*
 * CONCOCT composition+coverage binning (DAG node: mag_concoct; optional).
 */
process CONCOCT {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/mag.yml"

    publishDir "${params.outdir}/07_host_prediction/mag/concoct", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly), path(abundance)

    output:
    tuple val(meta), path("${meta.id}.concoct_out", type: 'dir'), emit: output_dir

    script:
    """
    concoct --composition_file ${assembly} --coverage_file ${abundance} \\
        -o ${meta.id}.concoct_out -t ${task.cpus}
    """
}
