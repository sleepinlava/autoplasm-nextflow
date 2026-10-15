/*
 * Dorado basecalling from ONT POD5 (DAG node: basecalling_dorado).
 * Dorado is not available on conda; install it manually (see envs/basecalling.yml).
 */
process DORADO_BASECALL {
    tag { meta.id }
    label 'process_medium'

    publishDir "${params.outdir}/00_input_validation/basecalling/${meta.id}", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(pod5)

    output:
    tuple val(meta), path("${meta.id}.dorado.fastq"), emit: long_reads

    script:
    def model = params.dorado_model ?: 'hac'
    """
    dorado basecaller ${model} ${pod5} --emit-fastq > ${meta.id}.dorado.fastq
    """
}
