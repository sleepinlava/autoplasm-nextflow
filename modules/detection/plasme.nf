/*
 * PLASMe plasmid classification (pipeline step: plasmid_detect_plasme;
 * optional, enabled via params.plasmid_detection_tools).
 */
process PLASME {
    cache 'deep'
    tag { meta.id }
    label 'process_medium'
    conda "${moduleDir}/../../envs/plasme.yml"
    container "${params.plasme_container ?: 'autoplasm-plasme:1.1'}"
    containerOptions workflow.containerEngine == 'podman' ? '--userns=keep-id --user $(id -u):$(id -g)' :
        workflow.containerEngine == 'docker' ? '--user $(id -u):$(id -g)' : ''

    publishDir "${params.outdir}/04_plasmid_detection/plasme", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly)
    tuple path(plasme_db, stageAs: 'plasme_database'), val(plasme_db_identity)
    tuple path(plasme_source, stageAs: 'plasme_source'), val(plasme_source_identity)
    // Explicit regular files: helper changes participate in deep caching.
    tuple path(autoplasm_helper_0, stageAs: 'normalize_plasme_outputs.py'), path(autoplasm_helper_1, stageAs: 'plasme_runtime.py')

    output:
    tuple val(meta), path("${meta.id}.plasme.tsv"), emit: predictions

    tuple val(meta), path("${meta.id}.plasme.fasta"), emit: plasmid_fasta
    tuple val(meta), path("${meta.id}.plasme_report.csv"), emit: report
    tuple val(meta), path("${meta.id}.plasme_runtime.json"), emit: runtime
    tuple val("${task.process}"), val(meta), path("${meta.id}.PLASME.task_command.sh"),
          val('python3 plasme_runtime.py -h'), eval('python3 plasme_runtime.py -h'),
          eval("sha256sum '${meta.id}.PLASME.task_command.sh'"), emit: task_provenance

    script:
    def shellQuote = { value -> "'" + value.toString().replace("'", "'\"'\"'") + "'" }
    def input_fasta = 'plasme_input.fasta'
    def prepare = assembly.name.toLowerCase().endsWith('.gz') ? "gzip -cd -- ${shellQuote.call(assembly)} > ${input_fasta}" : "ln -s -- ${shellQuote.call(assembly)} ${input_fasta}"
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.PLASME.task_command.sh'
    ${prepare}
    python3 plasme_runtime.py run --source-dir ${plasme_source} \\
        --assembly ${input_fasta} --database ${plasme_db} --output ${meta.id}.plasme \\
        --threads ${task.cpus} --runtime-record ${meta.id}.plasme_runtime.json
    python3 normalize_plasme_outputs.py --assembly ${shellQuote.call(input_fasta)} \\
        --plasmids ${meta.id}.plasme --report ${meta.id}.plasme_report.csv \\
        --output ${meta.id}.plasme.tsv
    mv ${meta.id}.plasme ${meta.id}.plasme.fasta
    """
}
