/*
 * Merge per-sample CoverM tables into a single long-format abundance table
 * (supports multisample_diversity / multisample_differential_abundance /
 * network / DESeq2 inputs). Implemented by bin/merge_abundance.py.
 */
process MERGE_ABUNDANCE {
    tag { label_name }
    label 'process_single'
    conda "${projectDir}/envs/python.yml"

    publishDir "${params.outdir}/tables", mode: params.publish_dir_mode

    input:
    path coverm_tables
    val label_name
    val id_column

    output:
    path "${label_name}.tsv", emit: table

    script:
    def files = (coverm_tables in List ? coverm_tables : [coverm_tables]).collect { it.toString() }.join(' ')
    """
    merge_abundance.py --tables ${files} --id-column ${id_column} --out ${label_name}.tsv
    """
}
