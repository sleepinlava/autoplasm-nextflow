/*
 * DESeq2 differential plasmid abundance (pipeline step:
 * multisample_differential_deseq2), implemented by bin/deseq2_plasmid.R.
 */
process DESEQ2 {
    tag 'deseq2'
    label 'process_medium'
    conda "${projectDir}/envs/deseq2.yml"
    container 'quay.io/biocontainers/bioconductor-deseq2:1.42.0--r43hf17093f_2'

    publishDir "${params.outdir}/11_diversity", mode: params.publish_dir_mode

    input:
    path(abundance_table, stageAs: 'abundance/*')
    path(sample_metadata, stageAs: 'cohort/*')

    path code_assets, stageAs: 'source_assets/*'

    output:
    path "differential_plasmids.tsv", emit: results
    path "deseq2_status.tsv", emit: status

    script:
    def minimum_replicates = params.min_group_replicates == null ? 3 : params.min_group_replicates
    def quote = { value -> "'" + value.toString().replace("'", "'\"'\"'") + "'" }
    """
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    Rscript analysis_code/deseq2_plasmid.R \\
        --abundance ${abundance_table} \\
        --metadata ${sample_metadata} \\
        --min-replicates ${quote.call(minimum_replicates)} \\
        --output differential_plasmids.tsv --out-status deseq2_status.tsv
    """
}
