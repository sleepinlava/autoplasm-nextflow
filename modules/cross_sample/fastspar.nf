/*
 * FastSpar plasmid co-occurrence network (pipeline step:
 * multisample_network_fastspar). Runs when at least params.network_min_samples
 * samples are present.
 */
process FASTSPAR {
    tag 'fastspar'
    label 'process_medium'
    conda "${projectDir}/envs/network.yml"
    container 'quay.io/biocontainers/fastspar:1.0.0--h1b620e3_6'

    publishDir "${params.outdir}/12_network", mode: params.publish_dir_mode

    input:
    path network_input

    output:
    path "correlation.tsv", emit: correlation
    path "covariance.tsv", emit: covariance

    script:
    """
    fastspar --otu_table ${network_input} \\
        --correlation correlation.tsv \\
        --covariance covariance.tsv \\
        --threads ${task.cpus}
    """
}
