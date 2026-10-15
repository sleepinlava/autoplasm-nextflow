/*
 * AutoPlasm Markdown + HTML report (DAG node: report_markdown; internal
 * report renderer in ABI, implemented here by bin/generate_report.py). The
 * script scans the published results directory and writes a simplified
 * summary report plus a methods section.
 */
process REPORT {
    tag 'report'
    label 'process_single'
    conda "${projectDir}/envs/python.yml"

    publishDir "${params.outdir}/report", mode: params.publish_dir_mode

    input:
    val trigger

    output:
    path "report.md", emit: report_md
    path "report.html", emit: report_html
    path "methods.md", emit: methods_md

    script:
    """
    generate_report.py \\
        --outdir ${params.outdir} \\
        --platform ${params.platform} \\
        --project-name ${params.project_name} \\
        --out-prefix .
    """
}
