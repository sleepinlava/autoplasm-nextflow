/*
 * minimap2 mapping of long reads to assembly contigs (DAG node:
 * contig_coverage_minimap2; mandatory on ont/pacbio_hifi/hybrid).
 */
process MINIMAP2_CONTIG_COVERAGE {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/alignment.yml"

    publishDir "${params.outdir}/02_assembly/coverage/minimap2", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly), path(long_reads)
    val preset

    output:
    tuple val(meta), path("${meta.id}.contig_alignment.sam"), emit: alignment

    script:
    """
    minimap2 -t ${task.cpus} -ax ${preset} ${assembly} ${long_reads} \\
        > ${meta.id}.contig_alignment.sam
    """
}
