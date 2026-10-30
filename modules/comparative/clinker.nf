/*
 * clinker synteny visualization across Bakta GenBank outputs (pipeline step:
 * comparative_clinker; optional via params.comparative_optional_tools).
 */
process CLINKER {
    tag { meta.id }
    label 'process_low'
    conda "${projectDir}/envs/comparative.yml"
    container 'quay.io/biocontainers/clinker-py:0.0.28--pyh7cba7a3_0'

    publishDir "${params.outdir}/09_comparative_genomics/clinker", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(bakta_dir)

    output:
    tuple val(meta), path("${meta.id}.clinker.html"), emit: html
    tuple val("${task.process}"), val(meta), path("${meta.id}.CLINKER.task_command.sh"),
          val('clinker --version'), eval('clinker --version'),
          eval("sha256sum '${meta.id}.CLINKER.task_command.sh'"), emit: task_provenance

    script:
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.CLINKER.task_command.sh'
    clinker ${bakta_dir}/*.gbff -p ${meta.id}.clinker.html
    """
}
