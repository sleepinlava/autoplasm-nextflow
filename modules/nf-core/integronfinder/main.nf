include { integronfinderRuntime; integronfinderRequireRuntime; integronfinderRuntimeBase64; integronfinderQuote } from '../../../lib/integronfinder_runtime'

process INTEGRONFINDER {
    cache 'deep'
    tag "${meta.id}"
    label 'process_low'

    containerOptions workflow.containerEngine in ['singularity', 'apptainer'] ?
        '--env MPLCONFIGDIR=/tmp/mplconfigdir' :
        '-e MPLCONFIGDIR=/tmp/mplconfigdir'

    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/integron_finder:2.0.5--pyhdfd78af_0':
        'quay.io/biocontainers/integron_finder:2.0.5--pyhdfd78af_0' }"

    input:
    tuple val(meta), path(fasta), val(runtime_identity), path(runtime_receipt)
    path(resource_helper, stageAs: 'integronfinder_runtime_resources.py')
    path(topology_helper, stageAs: 'integronfinder_topology.py')

    output:
    tuple val(meta), path("*/*.gbk")              , emit: gbk, optional: true
    tuple val(meta), path("*/*.integrons")        , emit: integrons
    tuple val(meta), path("*/*.summary")          , emit: summary
    tuple val(meta), path("*/integron_finder.out"), emit: out
    tuple val("${task.process}"), val('integronfinder'), eval("integron_finder --version 2>&1 | sed -n 's/^integron_finder version //p' | cut -d ' ' -f1 | grep -Fx '2.0.5'"), emit: versions_integronfinder, topic: versions
    tuple val("${task.process}"), val(meta), path("${meta.id}.INTEGRONFINDER.task_command.sh"),
          val('integron_finder --version'), eval('integron_finder --version'),
          eval("sha256sum '${meta.id}.INTEGRONFINDER.task_command.sh'"), emit: task_provenance

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def compressed = fasta.getName().endsWith('.gz')
    def name = fasta.getName().replace('.gz','')
    def runtime = integronfinderRuntime(task,workflow.containerEngine,meta)
    integronfinderRequireRuntime(runtime_identity,runtime)
    def encoded = integronfinderRuntimeBase64(runtime)
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.INTEGRONFINDER.task_command.sh'
    if [ '${compressed}' == 'true' ]; then
        gzip -c -d ${integronfinderQuote(fasta)} > ${integronfinderQuote(name)}
    fi
    python3 integronfinder_runtime_resources.py --runtime-base64 '${encoded}' --verify ${integronfinderQuote(runtime_receipt)} --execute -- ${args} --cpu ${task.cpus} ${integronfinderQuote(name)}
    """

    stub:
    integronfinderRequireRuntime(runtime_identity,integronfinderRuntime(task,workflow.containerEngine,meta))
    def args = task.ext.args ?: ''
    prefix = task.ext.prefix ?: "${meta.id}"
    def gbk_create = args.contains("--gbk") ? "touch Results_Integron_Finder_${prefix}/${prefix}.gbk" : ""

    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.INTEGRONFINDER.task_command.sh'
    mkdir -p Results_Integron_Finder_${prefix}
    ${gbk_create}
    touch "Results_Integron_Finder_${prefix}/${prefix}.integrons"
    touch "Results_Integron_Finder_${prefix}/${prefix}.summary"
    touch "Results_Integron_Finder_${prefix}/integron_finder.out"
    """
}

process INTEGRONFINDER_RESOURCE_PROBE {
    cache false
    tag "${meta.id}"
    label 'process_low'

    containerOptions workflow.containerEngine in ['singularity', 'apptainer'] ?
        '--env MPLCONFIGDIR=/tmp/mplconfigdir' :
        '-e MPLCONFIGDIR=/tmp/mplconfigdir'

    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/integron_finder:2.0.5--pyhdfd78af_0':
        'quay.io/biocontainers/integron_finder:2.0.5--pyhdfd78af_0' }"

    input:
    tuple val(meta), path(fasta)
    path(resource_helper, stageAs: 'integronfinder_runtime_resources.py')
    path(topology_helper, stageAs: 'integronfinder_topology.py')

    output:
    tuple val(meta), path('integronfinder_runtime_identity.json'), emit: identity

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def compressed = fasta.getName().endsWith('.gz')
    def name = fasta.getName().replace('.gz','')
    def encoded = integronfinderRuntimeBase64(integronfinderRuntime(task,workflow.containerEngine,meta))
    """
    if [ '${compressed}' == 'true' ]; then
        gzip -c -d ${integronfinderQuote(fasta)} > ${integronfinderQuote(name)}
    fi
    python3 integronfinder_runtime_resources.py --runtime-base64 '${encoded}' --output integronfinder_runtime_identity.json -- ${args} --cpu ${task.cpus} ${integronfinderQuote(name)}
    """

    stub:
    def encoded = integronfinderRuntimeBase64([schema_version:1,stub:true,runtime:integronfinderRuntime(task,workflow.containerEngine,meta)])
    """
    printf '%s' '${encoded}' | base64 -d > integronfinder_runtime_identity.json
    """
}
