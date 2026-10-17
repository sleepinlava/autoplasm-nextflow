/*
 * Platon plasmid detection (DAG node: plasmid_detect_platon; optional
 * consensus evidence). Requires the Platon database.
 */
process PLATON {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/platon.yml"
    // 版本对齐 envs/platon.yml 的 platon>=1.7 pin
    container 'quay.io/biocontainers/platon:1.7--pyhdfd78af_0'

    publishDir "${params.outdir}/04_plasmid_detection/platon", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly)
    path platon_db

    output:
    tuple val(meta), path("${meta.id}.platon.tsv"), emit: predictions
    tuple val(meta), path("${meta.id}.plasmid.fasta"), emit: plasmid_fasta, optional: true

    script:
    """
    platon --threads ${task.cpus} --output . --prefix ${meta.id} --meta \\
        --db ${platon_db} ${assembly}
    mv ${meta.id}.tsv ${meta.id}.platon.tsv
    """
}
