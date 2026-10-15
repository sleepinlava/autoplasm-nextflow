/*
 * samtools sort of a plasmid-abundance SAM alignment to BAM (DAG nodes:
 * abundance_samtools, abundance_samtools_short/long). label_suffix is '' for
 * single-mapper platforms and '.short'/'.long' for the hybrid chains.
 */
process SAMTOOLS_SORT_ABUND {
    tag { "${meta.id}${label_suffix}" }
    label 'process_medium'
    conda "${projectDir}/envs/abundance.yml"

    publishDir "${params.outdir}/10_abundance/samtools", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(alignment), val(label_suffix)

    output:
    tuple val(meta), path("${meta.id}${label_suffix}.bam"), val(label_suffix), emit: bam

    script:
    """
    samtools sort -@ ${task.cpus} -o ${meta.id}${label_suffix}.bam ${alignment}
    """
}
