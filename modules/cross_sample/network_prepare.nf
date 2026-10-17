/*
 * Prepare the compositional abundance matrix for FastSpar (DAG node:
 * multisample_network_prepare; internal handler in ABI, implemented here by
 * bin/network_prepare.R with prevalence filtering).
 */
process NETWORK_PREPARE {
    tag 'network_prepare'
    label 'process_single'
    conda "${projectDir}/envs/r_analysis.yml"
    // R 包集合以 envs/r_analysis.yml 为准；镜像需提供 data.table/vegan/Biostrings/Rsamtools
    container 'bioconductor/bioconductor_docker:RELEASE_3_21'

    publishDir "${params.outdir}/12_network", mode: params.publish_dir_mode

    input:
    path abundance_table

    output:
    path "fastspar_input.tsv", emit: network_input

    script:
    """
    network_prepare.R --abundance ${abundance_table} --out fastspar_input.tsv
    """
}
