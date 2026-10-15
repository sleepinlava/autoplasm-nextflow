/*
 * Bowtie2 host read removal for short reads (DAG node: host_removal_bowtie2;
 * optional, enabled when a host reference is configured).
 */
process BOWTIE2_HOST_REMOVAL {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/alignment.yml"

    publishDir "${params.outdir}/01_qc/host_removal/${meta.id}", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(read1), path(read2), path(host_reference)

    output:
    tuple val(meta), path("${meta.id}.host_removed.1.fastq.gz"), path("${meta.id}.host_removed.2.fastq.gz"), emit: reads
    tuple val(meta), path("${meta.id}.host.sam"), emit: host_alignment
    path "${meta.id}.host_removal.log", emit: log

    script:
    """
    bowtie2-build ${host_reference} host_index > /dev/null 2>&1
    bowtie2 -x host_index -1 ${read1} -2 ${read2} -p ${task.cpus} \\
        --un-conc-gz ${meta.id}.host_removed.%.fastq.gz \\
        -S ${meta.id}.host.sam \\
        2> ${meta.id}.host_removal.log
    """
}
