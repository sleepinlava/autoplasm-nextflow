/*
 * Bakta comprehensive plasmid annotation (DAG node: annotation_bakta; default
 * enabled). Requires the Bakta database.
 */
process BAKTA {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/annotation.yml"

    publishDir "${params.outdir}/08_annotation/bakta", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)
    path bakta_db

    output:
    tuple val(meta), path("${meta.id}.bakta_out", type: 'dir'), emit: output_dir
    tuple val(meta), path("${meta.id}.bakta_out/${meta.id}.tsv"), emit: annotations, optional: true
    tuple val(meta), path("${meta.id}.bakta_out/${meta.id}.gbff"), emit: genbank, optional: true

    script:
    """
    bakta --db ${bakta_db} --output ${meta.id}.bakta_out --threads ${task.cpus} \\
        --force --skip-sorf --prefix ${meta.id} ${plasmid_contigs}
    """
}
