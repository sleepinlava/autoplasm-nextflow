/*
 * samtools sort of a SAM alignment to BAM (DAG nodes: contig_coverage_samtools,
 * abundance_samtools, abundance_samtools_short/long). The output subdirectory
 * and file name travel with the tuple so the same module serves the contig
 * coverage and the plasmid abundance chains.
 */
process SAMTOOLS_SORT {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/abundance.yml"

    publishDir "${params.outdir}/${out_dir}", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(alignment), val(out_dir), val(out_name)

    output:
    tuple val(meta), path("${out_name}"), emit: bam

    script:
    """
    samtools sort -@ ${task.cpus} -o ${out_name} ${alignment}
    """
}

/*
 * samtools merge of per-mapper BAMs (hybrid contig coverage merges the
 * short-read and long-read alignments).
 */
process SAMTOOLS_MERGE {
    tag { meta.id }
    label 'process_low'
    conda "${projectDir}/envs/abundance.yml"

    publishDir "${params.outdir}/${out_dir}", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(bams), val(out_dir), val(out_name)

    output:
    tuple val(meta), path("${out_name}"), emit: bam

    script:
    def inputs = (bams instanceof List ? bams : [bams]).collect { it.toString() }.join(' ')
    """
    samtools merge -@ ${task.cpus} -o ${out_name} ${inputs}
    """
}
