/*
 * IntegronFinder integron detection (DAG node: annotation_integronfinder;
 * default enabled per config_default.yaml).
 */
process INTEGRONFINDER {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/integronfinder.yml"

    publishDir "${params.outdir}/08_annotation/integronfinder", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)

    output:
    tuple val(meta), path("${meta.id}.integronfinder_out", type: 'dir'), emit: results

    script:
    """
    integron_finder --outdir ${meta.id}.integronfinder_out --cpu ${task.cpus} \\
        ${plasmid_contigs}
    """
}
