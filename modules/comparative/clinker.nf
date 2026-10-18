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

    script:
    """
    clinker ${bakta_dir}/*.gbff -p ${meta.id}.clinker.html
    """
}
