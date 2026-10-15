/*
 * Prodigal gene calling on plasmid contigs (DAG node: annotation_prodigal;
 * optional).
 */
process PRODIGAL {
    tag { meta.id }
    label 'process_low'
    conda "${projectDir}/envs/annotation.yml"

    publishDir "${params.outdir}/08_annotation/${meta.id}/prodigal", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)

    output:
    tuple val(meta), path("${meta.id}.prodigal.gff"), emit: gene_calls
    tuple val(meta), path("${meta.id}.prodigal.faa"), emit: proteins
    tuple val(meta), path("${meta.id}.prodigal.ffn"), emit: nucleotides

    script:
    """
    prodigal -i ${plasmid_contigs} \\
        -o ${meta.id}.prodigal.gff \\
        -a ${meta.id}.prodigal.faa \\
        -d ${meta.id}.prodigal.ffn \\
        -p meta
    """
}
