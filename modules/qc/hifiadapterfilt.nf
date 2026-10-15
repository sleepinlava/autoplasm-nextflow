/*
 * HiFiAdapterFilt adapter removal for PacBio HiFi reads (DAG node:
 * qc_hifiadapterfilt; mandatory on pacbio_hifi).
 */
process HIFIADAPTERFILT {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/hifiadapterfilt.yml"

    publishDir "${params.outdir}/01_qc/${meta.id}", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(long_reads)

    output:
    tuple val(meta), path("${meta.id}.hifiadapterfilt.fastq.gz"), emit: reads

    script:
    def prefix = long_reads.name.replaceAll(/\.(fastq|fq)(\.gz)?$/, '')
    """
    # HiFiAdapterFilt writes <prefix>.filt.fastq.gz next to its working directory
    mkdir -p hifiadapterfilt_out
    cd hifiadapterfilt_out
    hifiadapterfilt.sh -t ${task.cpus} ../${long_reads}
    mv ${prefix}.filt.fastq.gz ../${meta.id}.hifiadapterfilt.fastq.gz
    """
}
