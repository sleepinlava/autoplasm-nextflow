/*
 * COPLA PTU classification (pipeline step: typing_copla; optional via
 * params.typing_optional_tools). Requires the COPLA reference graph/list.
 */
process COPLA {
    cache 'deep'
    tag { meta.id }
    label 'process_medium'
    conda "${moduleDir}/../../envs/copla.yml"

    publishDir "${params.outdir}/06_plasmid_typing/copla", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)
    path(copla_refgraph, stageAs: 'copla_reference.pickle')
    path(copla_reflist, stageAs: 'copla_references.fofn')
    tuple path(copla_install, stageAs: 'copla_install'), val(copla_install_identity)
    tuple path(copla_macsyfinder, stageAs: 'copla_macsyfinder'), val(copla_macsyfinder_identity)
    // Explicit regular files: helper changes participate in deep caching.
    path(autoplasm_helper_0, stageAs: 'run_copla_candidates.py')

    output:
    tuple val(meta), path("${meta.id}.copla.tsv"), emit: typing
    tuple val(meta), path("${meta.id}.copla"), emit: raw
    tuple val("${task.process}"), val(meta), path("${meta.id}.COPLA.task_command.sh"),
          val('python3 run_copla_candidates.py -h'), eval('python3 run_copla_candidates.py -h'),
          eval("sha256sum '${meta.id}.COPLA.task_command.sh'"), emit: task_provenance


    script:
    def shellQuote = { value -> "'" + value.toString().replace("'", "'\"'\"'") + "'" }
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.COPLA.task_command.sh'
    python3 run_copla_candidates.py --assembly ${shellQuote.call(plasmid_contigs)} \\
        --installation ${copla_install} --refgraph ${copla_refgraph} --reflist ${copla_reflist} \\
        --macsyfinder ${copla_macsyfinder} --threads ${task.cpus} \\
        --output ${meta.id}.copla.tsv --raw ${meta.id}.copla
    """
}
