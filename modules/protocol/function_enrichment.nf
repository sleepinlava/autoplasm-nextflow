process PROTOCOL_FUNCTION_ENRICHMENT {
    label 'process_single'
    conda "${projectDir}/envs/r_analysis.yml"
    container 'autoplasm-r-analysis:latest'
    publishDir "${params.outdir}/08_annotation/integrated", mode: params.publish_dir_mode
    cache 'deep'
    input:
    path annotations
    path systems
    path catalogue
    path code_assets,stageAs:'source_assets/*'
    output:
    path("*.task_command.sh"), emit: commands
    path('system_function_enrichment.tsv'), emit: enrichment
    path('comparative_figures'), emit: figures
    script:
    """
    cp -- "\${BASH_SOURCE[0]}" "${task.process.tokenize(':').last()}.task_command.sh"
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    export PYTHONPATH=\$PWD/analysis_code
    Rscript analysis_code/protocol_function_enrichment.R '${annotations}' '${systems}' '${catalogue}' system_function_enrichment.tsv comparative_figures
    """
}
