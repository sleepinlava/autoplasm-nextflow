/*
 * samtools sort of a contig-coverage SAM alignment to BAM (DAG node:
 * contig_coverage_samtools). label_suffix distinguishes the short-read and
 * long-read mapper chains on hybrid ('.short' / '.long').
 */
process SAMTOOLS_SORT {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/abundance.yml"

    publishDir "${params.outdir}/02_assembly/coverage/samtools", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(alignment), val(label_suffix)

    output:
    tuple val(meta), path("${meta.id}.contig_alignment${label_suffix}.bam"), emit: bam

    script:
    """
    samtools sort -@ ${task.cpus} -o ${meta.id}.contig_alignment${label_suffix}.bam ${alignment}
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

    publishDir "${params.outdir}/02_assembly/coverage/samtools", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(bams)

    output:
    tuple val(meta), path("${meta.id}.contig_alignment.bam"), emit: bam

    script:
    def inputs = (bams in List ? bams : [bams]).collect { it.toString() }.join(' ')
    """
    samtools merge -@ ${task.cpus} -o ${meta.id}.contig_alignment.bam ${inputs}
    """
}
