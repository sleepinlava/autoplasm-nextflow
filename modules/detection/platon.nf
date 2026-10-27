/*
 * Platon plasmid detection (pipeline step: plasmid_detect_platon; optional
 * consensus evidence). Requires the Platon database.
 */
process PLATON {
    tag { meta.id }
    label 'process_medium'
    cache 'deep'
    conda "${moduleDir}/../../envs/platon-linux-64.lock"
    container 'quay.io/biocontainers/platon:1.7--pyhdfd78af_0'

    publishDir "${params.outdir}/04_plasmid_detection/platon", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly, stageAs: 'assembly_input/*')
    tuple path(platon_db, stageAs: 'platon_database'), val(platon_database_identity)
    // Explicit regular files: helper changes participate in deep caching.
    path(autoplasm_helper_0, stageAs: 'platon_checked.py')

    output:
    tuple val(meta), path("${meta.id}.platon.tsv"), emit: predictions
    tuple val(meta), path("${meta.id}.plasmid.fasta"), emit: plasmid_fasta
    tuple val(meta), path("${meta.id}.json"), emit: details
    tuple val(meta), path("${meta.id}.platon_state.json"), emit: state
    tuple val(meta), path("${meta.id}.platon_runtime.json"), emit: runtime

    script:
    def quote = { value -> "'" + value.toString().replace("'", "'\"'\"'") + "'" }
    """
    python3 platon_checked.py --assembly ${quote.call(assembly)} --database platon_database \\
        --prefix ${quote.call(meta.id)} --record ${quote.call(meta.id + '.platon_runtime.json')} \\
        --threads ${task.cpus}
    mv ${quote.call(meta.id + '.tsv')} ${quote.call(meta.id + '.platon.tsv')}
    """
}
