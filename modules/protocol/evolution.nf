process PROTOCOL_EVOLUTION {
    label 'process_medium'
    conda "${projectDir}/envs/protocol_evolution.yml"
    publishDir "${params.outdir}/09_comparative_genomics/evolution", mode: params.publish_dir_mode
    cache 'deep'
    input:
    path annotations
    path systems
    path proteins,stageAs:'proteins??/*'
    path code_assets,stageAs:'source_assets/*'
    output:
    path("*.task_command.sh"), emit: commands
    path('evolution'), emit: evolution
    script:
    def aa=(proteins instanceof List ? proteins : [proteins]).collect { "'${it}'" }.join(' ')
    """
    cp -- "\${BASH_SOURCE[0]}" "${task.process.tokenize(':').last()}.task_command.sh"
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    export PYTHONPATH=\$PWD/analysis_code
    python3 analysis_code/protocol_evolution.py --annotations '${annotations}' --systems '${systems}' --proteins ${aa} \\
      --output evolution --threads ${task.cpus} --min-members ${params.protocol_tree_min_members} --min-core ${params.protocol_tree_min_core}
    """
}
