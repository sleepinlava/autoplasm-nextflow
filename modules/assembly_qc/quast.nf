/*
 * metaQUAST assembly quality assessment (DAG node: assembly_qc_quast;
 * mandatory on all platforms).
 */
process QUAST {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/assembly_qc.yml"

    publishDir "${params.outdir}/03_assembly_qc/${meta.id}", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly)

    output:
    tuple val(meta), path("report.tsv"), emit: report
    tuple val(meta), path("quast_out"), emit: output_dir

    script:
    """
    metaquast.py ${assembly} -o quast_out -t ${task.cpus} --max-ref-number 0
    cp quast_out/report.tsv report.tsv
    """
}
