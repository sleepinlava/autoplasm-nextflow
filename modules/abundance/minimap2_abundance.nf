/*
 * minimap2 mapping of long reads to plasmid contigs for abundance estimation
 * (DAG nodes: abundance_minimap2 and abundance_minimap2_long for hybrid).
 */
process MINIMAP2_ABUNDANCE {
    tag { "${meta.id}${label_suffix}" }
    label 'process_medium'
    conda "${projectDir}/envs/alignment.yml"

    publishDir "${params.outdir}/10_abundance/minimap2", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs), path(long_reads), val(label_suffix)
    val preset

    output:
    tuple val(meta), path("${meta.id}${label_suffix}.sam"), val(label_suffix), emit: alignment

    script:
    """
    minimap2 -t ${task.cpus} -ax ${preset} ${plasmid_contigs} ${long_reads} \\
        > ${meta.id}${label_suffix}.sam
    """
}
