/*
 * Merge per-sample CoverM tables into a single long-format abundance table
 * (supports multisample_diversity / multisample_differential_abundance /
 * network / DESeq2 inputs). Implemented by bin/merge_abundance.R.
 */
process MERGE_ABUNDANCE {
    tag { label_name }
    label 'process_single'
    conda "${projectDir}/envs/r_analysis.yml"
    // R 包集合以 envs/r_analysis.yml 为准；镜像需提供 data.table/vegan/Biostrings/Rsamtools
    container 'autoplasm-r-analysis:latest'

    publishDir "${params.outdir}/tables", mode: params.publish_dir_mode

    input:
    tuple val(sample_ids), path(coverm_tables)
    val label_name
    val id_column

    output:
    path "${label_name}.tsv", emit: table
    tuple val("${task.process}"), path("MERGE_ABUNDANCE.task_command.sh"),
          val('Rscript --version'), eval('Rscript --version'),
          eval("sha256sum 'MERGE_ABUNDANCE.task_command.sh'"),
          val((sample_ids instanceof List ? sample_ids : [sample_ids]).join(',')), emit: cohort_provenance

    script:
    def files = (coverm_tables in List ? coverm_tables : [coverm_tables])
        .collect { "'" + it.toString().replace("'", "'\"'\"'") + "'" }.join(' ')
    def ids = (sample_ids in List ? sample_ids : [sample_ids])
        .collect { "'" + it.toString().replace("'", "'\"'\"'") + "'" }.join(' ')
    """
    cp -- "\${BASH_SOURCE[0]}" 'MERGE_ABUNDANCE.task_command.sh'
    merge_abundance.R --tables ${files} --sample-ids ${ids} \\
        --id-column '${id_column}' --out '${label_name}.tsv'
    """
}
