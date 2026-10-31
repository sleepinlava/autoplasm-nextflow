process PROTOCOL_ANNOTATION_PRODUCTS {
    label 'process_single'
    conda "${projectDir}/envs/catalogue.yml"
    container 'python:3.12-slim'
    publishDir "${params.outdir}/08_annotation/integrated", mode: params.publish_dir_mode
    cache 'deep'
    input:
    path catalogue
    path systems
    path abundance
    path genes, stageAs:'genes??/*'
    path args, stageAs:'args??/*'
    path ises, stageAs:'ises??/*'
    path integrons, stageAs:'integrons??/*'
    path mobility, stageAs:'mobility??/*'
    path eggnog, stageAs:'eggnog??/*'
    path families, stageAs:'families??/*'
    path code_assets,stageAs:'source_assets/*'
    output:
    path("*.task_command.sh"), emit: commands
    path('annotations'), emit: products
    script:
    def q = { xs -> (xs instanceof List ? xs : [xs]).collect { "'${it}'" }.join(' ') }
    """
    cp -- "\${BASH_SOURCE[0]}" "${task.process.tokenize(':').last()}.task_command.sh"
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    export PYTHONPATH=\$PWD/analysis_code
    python3 analysis_code/protocol_annotation.py --catalogue '${catalogue}' --systems '${systems}' --abundance '${abundance}' \\
      --genes ${q.call(genes)} --args ${q.call(args)} --ises ${q.call(ises)} --integrons ${q.call(integrons)} \\
      --mobility ${q.call(mobility)} --eggnog ${q.call(eggnog)} --families ${q.call(families)} \\
      --output annotations --window ${params.protocol_arg_window} --min-breadth ${params.protocol_min_breadth} --min-depth ${params.protocol_min_depth}
    """
}
