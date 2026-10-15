/*
 * CoverM contig coverage estimation over the whole assembly (DAG node:
 * contig_coverage_coverm). The TSV carries mean/tpm/rpkm per contig and feeds
 * PlasMAAG binning and cross-sample diversity/differential analysis.
 */
process COVERM_CONTIG {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/abundance.yml"

    publishDir "${params.outdir}/02_assembly/coverage/${meta.id}", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(bam)

    output:
    tuple val(meta), path("${meta.id}.contig_coverm.tsv"), emit: table

    script:
    """
    coverm contig --bam-files ${bam} \\
        --output-file ${meta.id}.contig_coverm.tsv \\
        --methods mean tpm rpkm \\
        --min-covered-fraction 0 \\
        --threads ${task.cpus}
    """
}
