process PROTOCOL_CANDIDATES {
    tag { meta.id }
    label 'process_single'
    conda "${projectDir}/envs/catalogue.yml"
    container 'python:3.12-slim'
    publishDir { "${params.outdir}/04_plasmid_detection/protocol/${meta.id}" }, mode: params.publish_dir_mode
    cache 'deep'
    input:
    tuple val(meta), path(assembly), path(bins), path(summary), path(structure)
    path code_assets,stageAs:'source_assets/*'
    output:
    path("*.task_command.sh"), emit: commands
    tuple val(meta), path('candidates'), emit: candidates
    script:
    """
    cp -- "\${BASH_SOURCE[0]}" "${meta.id}.${task.process.tokenize(':').last()}.task_command.sh"
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    export PYTHONPATH=\$PWD/analysis_code
    python3 analysis_code/protocol_catalogue.py integrate --assembly ${assembly} --bins ${bins} --summary ${summary} \\
        --structure ${structure} --sample '${meta.id}' --output candidates --bin-score-threshold ${params.protocol_bin_score_threshold}
    """
}

process PROTOCOL_CATALOGUE_PREPARE {
    label 'process_single'
    conda "${projectDir}/envs/catalogue.yml"
    container 'python:3.12-slim'
    cache 'deep'
    input:
    tuple val(ids), path(assemblies, stageAs:'assemblies??/*'), path(candidates, stageAs:'candidates??/*')
    path complete_ids
    path code_assets,stageAs:'source_assets/*'
    output:
    path("*.task_command.sh"), emit: commands
    path('exact'), emit: exact
    script:
    def candidate_dirs = candidates instanceof List ? candidates : [candidates]
    def quote = { xs -> (xs instanceof List ? xs : [xs]).collect { "'${it}'" }.join(' ') }
    """
    cp -- "\${BASH_SOURCE[0]}" "${task.process.tokenize(':').last()}.task_command.sh"
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    export PYTHONPATH=\$PWD/analysis_code
    python3 analysis_code/protocol_catalogue.py prepare --ids ${quote.call(ids)} --assemblies ${quote.call(assemblies)} \\
        --candidates ${quote.call(candidate_dirs.collect { it.resolve('candidates.fasta') })} \\
        --evidence ${quote.call(candidate_dirs.collect { it.resolve('evidence.tsv') })} --output exact --complete-ids '${complete_ids}'
    """
}

process PROTOCOL_CATALOGUE_FINALIZE {
    label 'process_single'
    conda "${projectDir}/envs/catalogue.yml"
    container 'python:3.12-slim'
    publishDir "${params.outdir}/catalogue", mode: params.publish_dir_mode
    cache 'deep'
    input:
    path exact
    path clusters, stageAs:'clusters??/*'
    path complete_ids
    path code_assets,stageAs:'source_assets/*'
    output:
    path("*.task_command.sh"), emit: commands
    path('catalogue'), emit: catalogue
    script:
    def cluster_args = (clusters instanceof List ? clusters : [clusters]).collect { "'${it}'" }.join(' ')
    """
    cp -- "\${BASH_SOURCE[0]}" "${task.process.tokenize(':').last()}.task_command.sh"
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    export PYTHONPATH=\$PWD/analysis_code
    python3 analysis_code/protocol_catalogue.py finalize --exact ${exact} --clusters ${cluster_args} --output catalogue \\
        --identity ${params.catalogue_identity} --coverage ${params.catalogue_coverage} --complete-ids '${complete_ids}'
    """
}
