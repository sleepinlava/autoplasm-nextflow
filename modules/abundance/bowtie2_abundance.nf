/*
 * Bowtie2 mapping of short reads to plasmid contigs for abundance estimation
 * (DAG nodes: abundance_bowtie2 and abundance_bowtie2_short for hybrid).
 * label_suffix is '' for the primary chain and '.short' for the hybrid
 * short-read chain.
 */
process BOWTIE2_ABUNDANCE {
    tag { "${meta.id}${label_suffix}" }
    label 'process_medium'
    conda "${projectDir}/envs/alignment.yml"

    publishDir "${params.outdir}/10_abundance/bowtie2", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs), path(read1), path(read2), val(label_suffix)

    output:
    tuple val(meta), path("${meta.id}${label_suffix}.sam"), val(label_suffix), emit: alignment

    script:
    """
    bowtie2-build ${plasmid_contigs} plasmid_index > /dev/null 2>&1
    bowtie2 -x plasmid_index -1 ${read1} -2 ${read2} -p ${task.cpus} \\
        -S ${meta.id}${label_suffix}.sam
    """
}
