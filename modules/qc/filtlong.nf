/*
 * Filtlong long-read quality filtering (DAG node: qc_filtlong; mandatory on
 * ont/hybrid). Defaults mirror the ABI tool contract.
 */
process FILTLONG {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/qc_long.yml"

    publishDir "${params.outdir}/01_qc/${meta.id}", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(long_reads)

    output:
    tuple val(meta), path("${meta.id}.filtlong.fastq"), emit: reads

    script:
    """
    filtlong --min_length ${params.filtlong_min_length} --keep_percent ${params.filtlong_keep_percent} \
        ${long_reads} > ${meta.id}.filtlong.fastq
    """
}
