include { medakaRuntime; medakaRequireRuntime; medakaRuntimeBase64; medakaQuote } from '../../../lib/medaka_runtime'

process MEDAKA {
    cache 'deep'
    tag "$meta.id"
    label 'process_high'

    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/medaka:2.2.2--py312h3050eb1_0' :
        'quay.io/biocontainers/medaka:2.2.2--py312h3050eb1_0' }"

    input:
    tuple val(meta), path(reads), path(assembly), val(runtime_identity), path(runtime_receipt)
    path(resource_helpers, stageAs: '*')

    output:
    tuple val(meta), path("*.fa.gz"), emit: assembly
    tuple val("${task.process}"), val('medaka'), eval('medaka --version 2>&1 | sed "s/medaka //g"'), topic: versions, emit: versions_medaka

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    def runtime = medakaRuntime(task,workflow.containerEngine,meta)
    medakaRequireRuntime(runtime_identity,runtime)
    def encoded = medakaRuntimeBase64(runtime)
    """
    python3 medaka_runtime_resources.py --runtime-base64 '${encoded}' \\
        --reads ${medakaQuote(reads)} --assembly ${medakaQuote(assembly)} \\
        --verify ${medakaQuote(runtime_receipt)} --execute --threads $task.cpus -- $args

    mv consensus.fasta ${prefix}.fa

    gzip -n ${prefix}.fa

    """

    stub:
    medakaRequireRuntime(runtime_identity,medakaRuntime(task,workflow.containerEngine,meta))
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    echo "" | gzip > ${prefix}.fa.gz

    """
}

process MEDAKA_RESOURCE_PROBE {
    cache false
    tag "$meta.id"
    label 'process_low'

    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/medaka:2.2.2--py312h3050eb1_0' :
        'quay.io/biocontainers/medaka:2.2.2--py312h3050eb1_0' }"

    input:
    tuple val(meta), path(reads), path(assembly)
    path(resource_helpers, stageAs: '*')

    output:
    tuple val(meta), path('medaka_runtime_identity.json'), emit: identity

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def encoded = medakaRuntimeBase64(medakaRuntime(task,workflow.containerEngine,meta))
    """
    python3 medaka_runtime_resources.py --runtime-base64 '${encoded}' \\
        --reads ${medakaQuote(reads)} --assembly ${medakaQuote(assembly)} \\
        --output medaka_runtime_identity.json -- $args
    """

    stub:
    def encoded = medakaRuntimeBase64([schema:1,stub:true,runtime:medakaRuntime(task,workflow.containerEngine,meta)])
    """
    printf '%s' '${encoded}' | base64 -d > medaka_runtime_identity.json
    """
}
