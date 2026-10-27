include { abricateRuntime; abricateRequireRuntime; abricateRuntimeBase64; abricateQuote } from '../../../../lib/abricate_runtime'

process ABRICATE_RUN {
    cache 'deep'
    tag "${meta.id}"
    label 'process_medium'

    conda "${moduleDir}/environment.yml"
    container "${workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container
        ? 'https://depot.galaxyproject.org/singularity/abricate%3A1.0.1--ha8f3691_1'
        : 'quay.io/biocontainers/abricate:1.0.1--ha8f3691_1'}"

    input:
    tuple val(meta), path(assembly), val(runtime_identity), path(runtime_receipt)
    path databasedir
    path(resource_helper, stageAs: 'abricate_runtime_resources.pl')

    output:
    tuple val(meta), path("*.txt"), emit: report
    tuple val("${task.process}"), val('abricate'), eval("abricate --version | sed 's/^.* //' "), emit: versions_abricate, topic: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    def datadir = databasedir ? "--datadir ${abricateQuote(databasedir)}" : ''
    def runtime = abricateRuntime(task, workflow.containerEngine, meta, databasedir)
    abricateRequireRuntime(runtime_identity, runtime)
    def runtime64 = abricateRuntimeBase64(runtime)
    """
    if [[ ${abricateQuote(assembly)} != ${abricateQuote(prefix + '.fasta')} ]]; then
        ln -s ${abricateQuote(assembly)} ${abricateQuote(prefix + '.fasta')}
    fi
    perl abricate_runtime_resources.pl --runtime-base64 '${runtime64}' --verify ${abricateQuote(runtime_receipt)} --execute -- ${abricateQuote(prefix + '.fasta')} ${args} ${datadir} --threads ${task.cpus} > ${abricateQuote(prefix + '.txt')}
    """

    stub:
    abricateRequireRuntime(runtime_identity, abricateRuntime(task, workflow.containerEngine, meta, databasedir))
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    touch ${abricateQuote(prefix + '.txt')}
    """
}

process ABRICATE_RESOURCE_PROBE {
    cache false
    tag "${meta.id}"
    label 'process_medium'

    conda "${moduleDir}/environment.yml"
    container "${workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container
        ? 'https://depot.galaxyproject.org/singularity/abricate%3A1.0.1--ha8f3691_1'
        : 'quay.io/biocontainers/abricate:1.0.1--ha8f3691_1'}"

    input:
    tuple val(meta), path(assembly)
    path databasedir
    path(resource_helper, stageAs: 'abricate_runtime_resources.pl')

    output:
    tuple val(meta), path('abricate_runtime_identity.json'), emit: identity

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    def datadir = databasedir ? "--datadir ${abricateQuote(databasedir)}" : ''
    def runtime64 = abricateRuntimeBase64(abricateRuntime(task, workflow.containerEngine, meta, databasedir))
    """
    if [[ ${abricateQuote(assembly)} != ${abricateQuote(prefix + '.fasta')} ]]; then
        ln -s ${abricateQuote(assembly)} ${abricateQuote(prefix + '.fasta')}
    fi
    perl abricate_runtime_resources.pl --runtime-base64 '${runtime64}' --output abricate_runtime_identity.json -- ${abricateQuote(prefix + '.fasta')} ${args} ${datadir} --threads ${task.cpus}
    """

    stub:
    def encoded = abricateRuntimeBase64([schema_version:1, stub:true, runtime:abricateRuntime(task, workflow.containerEngine, meta, databasedir)])
    """
    printf '%s' '${encoded}' | base64 -d > abricate_runtime_identity.json
    """
}
