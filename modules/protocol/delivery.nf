process PROTOCOL_DELIVERY {
    label 'process_low'
    conda "${projectDir}/envs/protocol_delivery.yml"
    publishDir "${params.outdir}/final", mode: params.publish_dir_mode
    cache 'deep'
    input:
    path catalogue
    path systems
    path annotations
    path abundance
    path mags
    path metadata
    path host_results,stageAs:'host??/*'
    path strain_results,stageAs:'strain??/*'
    path evolution,stageAs:'evolution??/*'
    path extras,stageAs:'extras??/*'
    path source_code,stageAs:'source_snapshot/*'
    val settings
    val execution_records
    path code_assets,stageAs:'source_assets/*'
    output:
    path("*.task_command.sh"), emit: commands
    path('delivery'), emit: bundle
    script:
    def q = { xs -> (xs instanceof List ? xs : [xs]).collect { "'${it}'" }.join(' ') }
    """
    cp -- "\${BASH_SOURCE[0]}" "${task.process.tokenize(':').last()}.task_command.sh"
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    export PYTHONPATH=\$PWD/analysis_code
    cat > settings.json <<'PARAMS'
${groovy.json.JsonOutput.prettyPrint(groovy.json.JsonOutput.toJson(settings))}
PARAMS
    cat > execution_records.json <<'EXECUTION_RECORDS'
${groovy.json.JsonOutput.prettyPrint(groovy.json.JsonOutput.toJson(execution_records))}
EXECUTION_RECORDS
    python3 analysis_code/protocol_delivery.py --catalogue '${catalogue}' --systems '${systems}' --annotations '${annotations}' --abundance '${abundance}' \\
      --mags '${mags}' --metadata '${metadata}' --host-results ${q.call(host_results)} --strain-results ${q.call(strain_results)} \\
      --evolution ${q.call(evolution)} --extras ${q.call(extras)} source_snapshot --settings settings.json --execution-records execution_records.json --output delivery \\
      --min-breadth ${params.protocol_min_breadth} --min-depth ${params.protocol_min_depth} --strain-ani ${params.protocol_strain_ani} --min-compared-bases ${params.protocol_strain_min_compared_bases}
    """
}
