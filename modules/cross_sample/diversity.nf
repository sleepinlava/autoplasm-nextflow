/*
 * Alpha/beta diversity analysis (pipeline step: multisample_diversity,
 * implemented by bin/diversity.R with vegan). Runs when
 * at least params.min_diversity_samples samples are present.
 */
process DIVERSITY {
    tag 'diversity'
    label 'process_low'
    conda "${projectDir}/envs/r_analysis.yml"
    // R 包集合以 envs/r_analysis.yml 为准；镜像需提供 data.table/vegan/Biostrings/Rsamtools
    container 'autoplasm-r-analysis:latest'

    publishDir "${params.outdir}/11_diversity", mode: params.publish_dir_mode

    input:
    path abundance_table
    path sample_metadata

    output:
    path "diversity_metrics.tsv", emit: metrics
    path "bray_curtis_matrix.tsv", emit: beta

    script:
    """
    diversity.R --abundance ${abundance_table} --metadata ${sample_metadata} \\
        --out-metrics diversity_metrics.tsv \\
        --out-beta bray_curtis_matrix.tsv
    """
}
