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
    path "diversity_metrics.tsv", emit: metrics
    path "bray_curtis_matrix.tsv", emit: beta
    path "diversity_status.json", emit: status
    tuple val("${task.process}"), path("DIVERSITY.task_command.sh"),
          val('Rscript --version'), eval('Rscript --version'),
          eval("sha256sum 'DIVERSITY.task_command.sh'"),
          eval("cut -f1 cohort/* | tail -n +2 | sort -u | paste -sd, -"), emit: cohort_provenance

    script:
    """
    cp -- "\${BASH_SOURCE[0]}" 'DIVERSITY.task_command.sh'
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    Rscript analysis_code/diversity.R --abundance ${abundance_table} --metadata ${sample_metadata} \\
        --out-metrics diversity_metrics.tsv \\
        --out-beta bray_curtis_matrix.tsv --out-status diversity_status.json
    """
}
