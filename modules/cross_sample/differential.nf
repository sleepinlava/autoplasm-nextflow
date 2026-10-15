/*
 * Internal effect-size differential plasmid abundance (DAG node:
 * multisample_differential_abundance; internal handler in ABI, implemented
 * here by bin/differential_abundance.py).
 */
process DIFFERENTIAL_ABUNDANCE {
    tag 'differential'
    label 'process_low'
    conda "${projectDir}/envs/python.yml"

    publishDir "${params.outdir}/11_diversity", mode: params.publish_dir_mode

    input:
    path abundance_table
    path sample_metadata

    output:
    path "differential_abundance.tsv", emit: results

    script:
    """
    differential_abundance.py --abundance ${abundance_table} \\
        --metadata ${sample_metadata} \\
        --min-replicates ${params.min_group_replicates} \\
        --out differential_abundance.tsv
    """
}
