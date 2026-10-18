/*
 * AutoPlasm Markdown + HTML report (pipeline step: report_markdown,
 * implemented by bin/generate_report.R). The script scans the published
 * results directory and writes a summary report plus a methods section.
 */
process REPORT {
    tag 'report'
    label 'process_single'
    conda "${projectDir}/envs/r_analysis.yml"
    // R 包集合以 envs/r_analysis.yml 为准；镜像需提供 data.table/vegan/Biostrings/Rsamtools
    container 'autoplasm-r-analysis:latest'

    publishDir "${params.outdir}/report", mode: params.publish_dir_mode

    input:
    val trigger

    output:
    path "report.md", emit: report_md
    path "report.html", emit: report_html
    path "methods.md", emit: methods_md

    script:
    """
    generate_report.R \\
        --outdir ${params.outdir} \\
        --platform ${params.platform} \\
        --project-name ${params.project_name} \\
        --template ${projectDir}/assets/plasmid_report.Rmd \\
        --out-prefix .
    """
}
