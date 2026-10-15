/*
 * minimap2 host read removal for long reads (DAG node: host_removal_minimap2_long;
 * optional, enabled when a host reference is configured).
 */
process MINIMAP2_HOST_REMOVAL {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/alignment.yml"

    publishDir "${params.outdir}/01_qc/host_removal/minimap2", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(long_reads), path(host_reference)
    val preset

    output:
    tuple val(meta), path("${meta.id}.host_removed.fastq"), emit: reads
    tuple val(meta), path("${meta.id}.host_reads.fastq"), emit: host_reads

    script:
    """
    minimap2 -t ${task.cpus} -ax ${preset} ${host_reference} ${long_reads} \\
        | samtools fastq -f 4 - > ${meta.id}.host_removed.fastq
    minimap2 -t ${task.cpus} -ax ${preset} ${host_reference} ${long_reads} \\
        | samtools fastq -F 4 - > ${meta.id}.host_reads.fastq
    """
}
