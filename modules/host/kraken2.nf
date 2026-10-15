/*
 * Kraken2 taxonomic classification (DAG node: host_prediction_kraken2;
 * optional, illumina only). Requires a Kraken2 database.
 */
process KRAKEN2 {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/host_prediction.yml"

    publishDir "${params.outdir}/07_host_prediction/kraken2", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(read1), path(read2)
    path kraken2_db

    output:
    tuple val(meta), path("${meta.id}.kraken2.report"), emit: report

    script:
    """
    kraken2 --threads ${task.cpus} --db ${kraken2_db} \\
        --report ${meta.id}.kraken2.report \\
        --paired ${read1} ${read2}
    """
}
