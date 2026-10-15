/*
 * Alpha/beta diversity analysis (DAG node: multisample_diversity; internal
 * handler in ABI, implemented here by bin/diversity.py). Runs when at least
 * params.min_diversity_samples samples are present.
 */
process DIVERSITY {
    tag 'diversity'
    label 'process_low'
    conda "${projectDir}/envs/python.yml"

    publishDir "${params.outdir}/11_diversity", mode: params.publish_dir_mode

    input:
    path abundance_table
    path sample_metadata

    output:
    path "diversity_metrics.tsv", emit: metrics
    path "bray_curtis_matrix.tsv", emit: beta

    script:
    """
    diversity.py --abundance ${abundance_table} --metadata ${sample_metadata} \\
        --out-metrics diversity_metrics.tsv \\
        --out-beta bray_curtis_matrix.tsv
    """
}
