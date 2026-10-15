/*
 * Bowtie2 mapping of short reads to assembly contigs (DAG node:
 * contig_coverage_bowtie2; mandatory on illumina/hybrid).
 */
process BOWTIE2_CONTIG_COVERAGE {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/alignment.yml"

    publishDir "${params.outdir}/02_assembly/coverage/bowtie2", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly), path(read1), path(read2)

    output:
    tuple val(meta), path("${meta.id}.contig_alignment.sam"), emit: alignment

    script:
    """
    bowtie2-build ${assembly} contig_index > /dev/null 2>&1
    bowtie2 -x contig_index -1 ${read1} -2 ${read2} -p ${task.cpus} \\
        -S ${meta.id}.contig_alignment.sam
    """
}
