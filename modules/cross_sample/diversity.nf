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
    path(abundance_table, stageAs: 'abundance/*')
    path(sample_metadata, stageAs: 'cohort/*')

    path code_assets, stageAs: 'source_assets/*'

    output:
    path "${prefix}diversity_metrics.tsv", emit: metrics
    path "${prefix}bray_curtis_matrix.tsv", emit: beta
    path "${prefix}diversity_status.json", emit: status
    path "${prefix}ecology", emit: inference
    path "${prefix}r_package_versions.tsv", emit: versions_r_packages
    tuple val("${task.process}"), path("DIVERSITY.task_command.sh"),
          val('Rscript --version'), eval('Rscript --version'),
          eval("sha256sum 'DIVERSITY.task_command.sh'"),
          eval("cut -f1 cohort/* | tail -n +2 | sort -u | paste -sd, -"), emit: cohort_provenance

    script:
    prefix = params.short_read_protocol ? (task.process.tokenize(':').last() == 'SYSTEM_DIVERSITY' ? 'systems.' : 'plasmids.') : ''
    def q = { value -> "'" + value.toString().replace("'", "'\"'\"'") + "'" }
    """
    cp -- "\${BASH_SOURCE[0]}" 'DIVERSITY.task_command.sh'
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    Rscript analysis_code/diversity.R --abundance ${abundance_table} --metadata ${sample_metadata} \\
        --out-metrics '${prefix}diversity_metrics.tsv' \\
        --out-beta '${prefix}bray_curtis_matrix.tsv' --out-status '${prefix}diversity_status.json' \\
        --beta-normalization ${q.call(params.beta_normalization)} --inference-dir '${prefix}ecology' \\
        --formula ${q.call(params.ecology_formula)} --block ${q.call(params.ecology_block ?: "")} --permutations ${params.ecology_permutations}
    Rscript -e 'write.table(installed.packages()[,c("Package","Version")],"${prefix}r_package_versions.tsv",sep="\\t",row.names=FALSE,quote=FALSE)'
    """
}
