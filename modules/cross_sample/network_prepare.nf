/*
 * Prepare the compositional abundance matrix for FastSpar (pipeline step:
 * multisample_network_prepare, implemented by bin/network_prepare.R with
 * prevalence filtering).
 */
process NETWORK_PREPARE {
    tag 'network_prepare'
    label 'process_single'
    conda "${projectDir}/envs/r_analysis.yml"
    // R 包集合以 envs/r_analysis.yml 为准；镜像需提供 data.table/vegan/Biostrings/Rsamtools
    container 'autoplasm-r-analysis:latest'

    publishDir "${params.outdir}/12_network", mode: params.publish_dir_mode

    input:
    path(abundance_table, stageAs: 'abundance/*')
    path(sample_metadata, stageAs: 'cohort/*')

    path code_assets, stageAs: 'source_assets/*'

    output:
    path "fastspar_input.tsv", emit: network_input
    path "network_status.json", emit: status
    path "fastspar_eligible.tsv", optional: true, emit: eligible_input
    tuple val("${task.process}"), path("NETWORK_PREPARE.task_command.sh"),
          val('Rscript --version'), eval('Rscript --version'),
          eval("sha256sum 'NETWORK_PREPARE.task_command.sh'"),
          eval("cut -f1 cohort/* | tail -n +2 | sort -u | paste -sd, -"), emit: cohort_provenance

    script:
    def quote = { value -> "'" + value.toString().replace("'", "'\"'\"'") + "'" }
    def metadata_arg = sample_metadata ? "--metadata ${quote.call(sample_metadata)}" : ''
    def minimum_samples = params.network_min_samples == null ? 20 : params.network_min_samples
    """
    cp -- "\${BASH_SOURCE[0]}" 'NETWORK_PREPARE.task_command.sh'
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    Rscript analysis_code/network_prepare.R --abundance ${abundance_table} ${metadata_arg} \\
      --min-samples ${quote.call(minimum_samples)} --out fastspar_input.tsv \\
      --out-status network_status.json --eligible-out fastspar_eligible.tsv
    """
}
