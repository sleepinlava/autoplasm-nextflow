/*
 * IntegronFinder integron detection (DAG node: annotation_integronfinder;
 * default enabled per config_default.yaml).
 */
process INTEGRONFINDER {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/integronfinder.yml"

    publishDir "${params.outdir}/08_annotation/${meta.id}/integronfinder", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)

    output:
    tuple val(meta), path("integronfinder_out"), emit: results

    script:
    """
    integron_finder --outdir integronfinder_out --cpu ${task.cpus} \\
        ${plasmid_contigs}
    """
}
