/*
 * Prepare the compositional abundance matrix for FastSpar (DAG node:
 * multisample_network_prepare; internal handler in ABI, implemented here by
 * bin/network_prepare.py).
 */
process NETWORK_PREPARE {
    tag 'network_prepare'
    label 'process_single'
    conda "${projectDir}/envs/python.yml"

    publishDir "${params.outdir}/12_network", mode: params.publish_dir_mode

    input:
    path abundance_table

    output:
    path "fastspar_input.tsv", emit: network_input

    script:
    """
    network_prepare.py --abundance ${abundance_table} --out fastspar_input.tsv
    """
}
