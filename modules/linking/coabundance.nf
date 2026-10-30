/*
 * Co-abundance correlation host-plasmid linking (pipeline step:
 * host_plasmid_link_coabundance, implemented by bin/coabundance_link.R).
 * Cross-sample: correlates plasmid coverage with
 * MetaPhlAn host abundance across samples, with cor.test p-values, BH FDR
 * and a presence/absence Jaccard score in supporting_data.
 */
process LINK_COABUNDANCE {
    tag 'coabundance'
    label 'process_low'
    conda "${projectDir}/envs/r_analysis.yml"
    // R 包集合以 envs/r_analysis.yml 为准；镜像需提供 data.table/vegan/Biostrings/Rsamtools
    container 'autoplasm-r-analysis:latest'

    publishDir "${params.outdir}/07_host_prediction", mode: params.publish_dir_mode

    input:
    path plasmid_abundance_merged
    tuple val(host_sample_ids), path(host_profiles)

    output:
    path "coabundance_links.tsv", emit: links
    tuple val("${task.process}"), path("LINK_COABUNDANCE.task_command.sh"),
          val('Rscript --version'), eval('Rscript --version'),
          eval("sha256sum 'LINK_COABUNDANCE.task_command.sh'"),
          val((host_sample_ids instanceof List ? host_sample_ids : [host_sample_ids]).join(',')), emit: cohort_provenance


    script:
    def shellQuote = { value -> "'" + value.toString().replace("'", "'\"'\"'") + "'" }
    def profileFiles = (host_profiles in List ? host_profiles : (host_profiles ? [host_profiles] : []))
        .collect { shellQuote.call(it) }.join(' ')
    def sampleIds = (host_sample_ids in List ? host_sample_ids : (host_sample_ids ? [host_sample_ids] : []))
        .collect { shellQuote.call(it) }.join(' ')
    """
    cp -- "\${BASH_SOURCE[0]}" 'LINK_COABUNDANCE.task_command.sh'
    coabundance_link.R \\
        --plasmid-abundance ${shellQuote.call(plasmid_abundance_merged)} \\
        --host-profiles ${profileFiles} \\
        --host-sample-ids ${sampleIds} \\
        --method ${params.link_correlation_method} \\
        --min-correlation ${params.link_min_correlation} \\
        --out coabundance_links.tsv
    """
}
