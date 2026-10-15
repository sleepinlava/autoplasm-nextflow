/*
 * MOB-suite plasmid annotation and reconstruction (DAG node:
 * annotation_mob_suite; optional via params.annotation_optional_tools).
 */
process MOB_SUITE_ANNOT {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/mob_suite.yml"

    publishDir "${params.outdir}/08_annotation/mob_suite", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)
    path mob_db

    output:
    tuple val(meta), path("${meta.id}.mob_suite_out", type: 'dir'), emit: output_dir

    script:
    """
    mob_recon --infile ${plasmid_contigs} --outdir ${meta.id}.mob_suite_out \\
        --num_threads ${task.cpus} --database_directory ${mob_db}
    """
}
