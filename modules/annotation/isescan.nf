include { isescanRuntime; isescanRequireRuntime; isescanRuntimeBase64; isescanQuote } from '../../lib/isescan_runtime'

/* Fixed native1.7.3; resources are resolved before the scientific cache lookup. */
process ISESCAN {
    cache 'deep'
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/isescan.yml"
    container 'quay.io/biocontainers/isescan:1.7.3--hab16a5f_1'
    publishDir "${params.outdir}/08_annotation/isescan", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs), val(runtime_identity), path(runtime_receipt)
    path(resource_helper, stageAs: 'isescan_runtime_resources.py')

    output:
    tuple val(meta), path("${meta.id}.isescan_out", type: 'dir'), emit: results

    script:
    def runtime = isescanRuntime(task, workflow.containerEngine, meta)
    isescanRequireRuntime(runtime_identity, runtime)
    def runtime64 = isescanRuntimeBase64(runtime)
    def seqfile = isescanQuote(plasmid_contigs)
    def prefix = isescanQuote("${meta.id}.isescan_out")
    """
    python3 isescan_runtime_resources.py --runtime-base64 '${runtime64}' --seqfile ${seqfile} --result-prefix ${prefix} --threads ${task.cpus} --verify ${runtime_receipt} --execute
    """

    stub:
    isescanRequireRuntime(runtime_identity, isescanRuntime(task, workflow.containerEngine, meta))
    def prefix = isescanQuote("${meta.id}.isescan_out")
    """
    mkdir -p ${prefix}
    printf '%s\n' '{"state":"stub_not_validated","inference":false}' > ${prefix}/isescan_stub.json
    """
}

process ISESCAN_RESOURCE_PROBE {
    cache false
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/isescan.yml"
    container 'quay.io/biocontainers/isescan:1.7.3--hab16a5f_1'

    input:
    tuple val(meta), path(plasmid_contigs)
    path(resource_helper, stageAs: 'isescan_runtime_resources.py')

    output:
    tuple val(meta), path('isescan_runtime_identity.json'), emit: identity

    script:
    def runtime64 = isescanRuntimeBase64(isescanRuntime(task, workflow.containerEngine, meta))
    def seqfile = isescanQuote(plasmid_contigs)
    def prefix = isescanQuote("${meta.id}.isescan_out")
    """
    python3 isescan_runtime_resources.py --runtime-base64 '${runtime64}' --seqfile ${seqfile} --result-prefix ${prefix} --threads ${task.cpus} --output isescan_runtime_identity.json
    """

    stub:
    def identity = [schema_version: 1, stub: true, runtime: isescanRuntime(task, workflow.containerEngine, meta)]
    def encoded = isescanRuntimeBase64(identity)
    """
    printf '%s' '${encoded}' | base64 -d > isescan_runtime_identity.json
    """
}
