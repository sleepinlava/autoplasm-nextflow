/*
 * ABRicate multi-database ARG/VF screening (DAG node: annotation_abricate;
 * optional via params.annotation_tools; database selected by
 * params.abricate_db, default card).
 */
process ABRICATE {
    tag { meta.id }
    label 'process_low'
    conda "${projectDir}/envs/annotation.yml"

    publishDir "${params.outdir}/08_annotation/abricate", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)

    output:
    tuple val(meta), path("${meta.id}.${params.abricate_db}.tsv"), emit: results

    script:
    """
    abricate --threads ${task.cpus} --db ${params.abricate_db} \\
        ${plasmid_contigs} > ${meta.id}.${params.abricate_db}.tsv
    """
}
