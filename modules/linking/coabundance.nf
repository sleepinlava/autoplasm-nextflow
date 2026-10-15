/*
 * Co-abundance correlation host-plasmid linking (DAG node:
 * host_plasmid_link_coabundance; internal handler in ABI, implemented here by
 * bin/coabundance_link.py). Cross-sample: correlates plasmid coverage with
 * MetaPhlAn host abundance across samples.
 */
process LINK_COABUNDANCE {
    tag 'coabundance'
    label 'process_low'
    conda "${projectDir}/envs/python.yml"

    publishDir "${params.outdir}/07_host_prediction", mode: params.publish_dir_mode

    input:
    path plasmid_abundance_merged
    path host_profiles

    output:
    path "coabundance_links.tsv", emit: links

    script:
    """
    coabundance_link.py \\
        --plasmid-abundance ${plasmid_abundance_merged} \\
        --host-profiles ${host_profiles} \\
        --method ${params.link_correlation_method} \\
        --min-correlation ${params.link_min_correlation} \\
        --out coabundance_links.tsv
    """
}
