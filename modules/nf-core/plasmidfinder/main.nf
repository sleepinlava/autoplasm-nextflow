include { plasmidfinderRuntime; plasmidfinderRequireRuntime; plasmidfinderRuntimeBase64; plasmidfinderQuote } from '../../../lib/plasmidfinder_runtime'

process PLASMIDFINDER {
    cache 'deep'
    tag "$meta.id"
    label 'process_low'

    // WARN: Version information not provided by tool on CLI. Please update version string below when bumping container versions.
    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/plasmidfinder:2.1.6--py310hdfd78af_1':
        'quay.io/biocontainers/plasmidfinder:2.1.6--py310hdfd78af_1' }"

    input:
    tuple val(meta), path(fasta), val(runtime_identity), path(runtime_receipt)
    path(resource_helper, stageAs: 'plasmidfinder_runtime_resources.py')

    output:
    tuple val(meta), path("*.json")                 , emit: json
    tuple val(meta), path("*.txt")                  , emit: txt
    tuple val(meta), path("*.tsv")                  , emit: tsv
    tuple val(meta), path("*-hit_in_genome_seq.fsa"), emit: genome_seq
    tuple val(meta), path("*-plasmid_seqs.fsa")     , emit: plasmid_seq
    tuple val("${task.process}"), val('plasmidfinder'), val('2.1.6'), topic: versions, emit: versions_plasmidfinder
    // WARN: Version information not provided by tool on CLI. Please update this string when bumping container versions.

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    def is_compressed = fasta.getName().endsWith(".gz") ? true : false
    def fasta_name = fasta.getName().replace(".gz", "")
    def runtime = plasmidfinderRuntime(task,workflow.containerEngine,meta)
    plasmidfinderRequireRuntime(runtime_identity,runtime)
    def encoded = plasmidfinderRuntimeBase64(runtime)
    """
    if [ "$is_compressed" == "true" ]; then
        gzip -c -d ${plasmidfinderQuote(fasta)} > ${plasmidfinderQuote(fasta_name)}
    fi
    python3 plasmidfinder_runtime_resources.py --runtime-base64 '${encoded}' --verify ${plasmidfinderQuote(runtime_receipt)} --execute -- ${args} -i ${plasmidfinderQuote(fasta_name)} -o ./ -x

    # Rename hard-coded outputs with prefix to avoid name collisions
    mv data.json ${prefix}.json
    mv results.txt ${prefix}.txt
    mv results_tab.tsv ${prefix}.tsv
    mv Hit_in_genome_seq.fsa ${prefix}-hit_in_genome_seq.fsa
    mv Plasmid_seqs.fsa ${prefix}-plasmid_seqs.fsa

    """

    stub:
    plasmidfinderRequireRuntime(runtime_identity,plasmidfinderRuntime(task,workflow.containerEngine,meta))
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    touch ${prefix}.json
    touch ${prefix}.txt
    touch ${prefix}.tsv
    touch ${prefix}-hit_in_genome_seq.fsa
    touch ${prefix}-plasmid_seqs.fsa
    """
}

process PLASMIDFINDER_RESOURCE_PROBE {
    cache false
    tag "${meta.id}"
    label 'process_low'

    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/plasmidfinder:2.1.6--py310hdfd78af_1':
        'quay.io/biocontainers/plasmidfinder:2.1.6--py310hdfd78af_1' }"

    input:
    tuple val(meta), path(fasta)
    path(resource_helper, stageAs: 'plasmidfinder_runtime_resources.py')

    output:
    tuple val(meta), path('plasmidfinder_runtime_identity.json'), emit: identity

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def compressed = fasta.getName().endsWith('.gz')
    def name = fasta.getName().replace('.gz','')
    def encoded = plasmidfinderRuntimeBase64(plasmidfinderRuntime(task,workflow.containerEngine,meta))
    """
    if [ '${compressed}' == 'true' ]; then
        gzip -c -d ${plasmidfinderQuote(fasta)} > ${plasmidfinderQuote(name)}
    fi
    python3 plasmidfinder_runtime_resources.py --runtime-base64 '${encoded}' --output plasmidfinder_runtime_identity.json -- ${args} -i ${plasmidfinderQuote(name)} -o ./ -x
    """

    stub:
    def encoded = plasmidfinderRuntimeBase64([schema_version:1,stub:true,runtime:plasmidfinderRuntime(task,workflow.containerEngine,meta)])
    """
    printf '%s' '${encoded}' | base64 -d > plasmidfinder_runtime_identity.json
    """
}
