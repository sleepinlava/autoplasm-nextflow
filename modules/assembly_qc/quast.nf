/*
 * metaQUAST assembly quality assessment (DAG node: assembly_qc_quast;
 * mandatory on all platforms).
 */
process QUAST {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/assembly_qc.yml"

    publishDir "${params.outdir}/03_assembly_qc/quast", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly)

    output:
    tuple val(meta), path("${meta.id}.quast_report.tsv"), emit: report
    tuple val(meta), path("${meta.id}.quast_out"), emit: output_dir

    script:
    """
    metaquast.py ${assembly} -o ${meta.id}.quast_out -t ${task.cpus} --max-ref-number 0
    cp ${meta.id}.quast_out/report.tsv ${meta.id}.quast_report.tsv
    """
}
