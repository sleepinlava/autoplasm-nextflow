/*
 * Internal effect-size differential plasmid abundance (DAG node:
 * multisample_differential_abundance; internal handler in ABI, implemented
 * here by bin/differential_abundance.R with prevalence filtering).
 */
process DIFFERENTIAL_ABUNDANCE {
    tag 'differential'
    label 'process_low'
    conda "${projectDir}/envs/r_analysis.yml"
    // R 包集合以 envs/r_analysis.yml 为准；镜像需提供 data.table/vegan/Biostrings/Rsamtools
    container 'bioconductor/bioconductor_docker:RELEASE_3_21'

    publishDir "${params.outdir}/11_diversity", mode: params.publish_dir_mode

    input:
    path abundance_table
    path sample_metadata

    output:
    path "differential_abundance.tsv", emit: results

    script:
    """
    differential_abundance.R --abundance ${abundance_table} \\
        --metadata ${sample_metadata} \\
        --min-replicates ${params.min_group_replicates} \\
        --out differential_abundance.tsv
    """
}
