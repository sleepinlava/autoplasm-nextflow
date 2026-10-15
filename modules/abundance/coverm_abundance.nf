/*
 * CoverM plasmid abundance estimation (DAG nodes: abundance_coverm and the
 * hybrid short/long variants). Emits mean/tpm/rpkm per plasmid contig.
 */
process COVERM_ABUNDANCE {
    tag { "${meta.id}${label_suffix}" }
    label 'process_medium'
    conda "${projectDir}/envs/abundance.yml"

    publishDir "${params.outdir}/10_abundance/coverm", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(bam), val(label_suffix)

    output:
    tuple val(meta), path("${meta.id}${label_suffix}.coverm.tsv"), emit: abundance

    script:
    """
    coverm contig --bam-files ${bam} \\
        --output-file ${meta.id}${label_suffix}.coverm.tsv \\
        --methods mean tpm rpkm \\
        --min-covered-fraction 0 \\
        --threads ${task.cpus}
    """
}
