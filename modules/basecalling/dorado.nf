/*
 * Dorado basecalling from ONT POD5 (pipeline step: basecalling_dorado).
 * Dorado has no bioconda package and no community container is pinned by the
 * project, so this process deliberately ships no `container` directive: with
 * docker/singularity profiles enabled Nextflow will run it in the default
 * `ontresearch/dorado:latest` image only if the deployment provides one.
 * Install dorado manually (see envs/basecalling.yml) and keep it on PATH.
 */
process DORADO_BASECALL {
    tag { meta.id }
    label 'process_medium'

    publishDir "${params.outdir}/00_input_validation/basecalling/dorado", mode: params.publish_dir_mode

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
