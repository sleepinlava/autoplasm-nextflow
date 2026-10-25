/*
 * Internal effect-size differential plasmid abundance (pipeline step:
 * multisample_differential_abundance, implemented by
 * bin/differential_abundance.R with prevalence filtering).
 */
process DIFFERENTIAL_ABUNDANCE {
    tag 'differential'
    label 'process_low'
    conda "${projectDir}/envs/r_analysis.yml"
    // R 包集合以 envs/r_analysis.yml 为准；镜像需提供 data.table/vegan/Biostrings/Rsamtools
    container 'autoplasm-r-analysis:latest'

    publishDir "${params.outdir}/11_diversity", mode: params.publish_dir_mode

    input:
    path(abundance_table, stageAs: 'abundance/*')
    path(sample_metadata, stageAs: 'cohort/*')

    path code_assets, stageAs: 'source_assets/*'

    output:
    path "differential_abundance.tsv", emit: results

    script:
    def minimum_replicates = params.min_group_replicates == null ? 3 : params.min_group_replicates
    def quote = { value -> "'" + value.toString().replace("'", "'\"'\"'") + "'" }
    """
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    Rscript analysis_code/differential_abundance.R --abundance ${abundance_table} \\
        --metadata ${sample_metadata} \\
        --min-replicates ${quote.call(minimum_replicates)} \\
        --out differential_abundance.tsv
    """
}
