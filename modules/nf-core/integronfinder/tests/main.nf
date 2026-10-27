nextflow.enable.dsl=2
include { INTEGRONFINDER; INTEGRONFINDER_RESOURCE_PROBE } from '../main'
include { integronfinderResourceRecord } from '../../../../lib/integronfinder_runtime'

process ORIGINAL_LINEAR_REFERENCE {
    label 'process_low'
    conda "${moduleDir}/../environment.yml"
    container 'quay.io/biocontainers/integron_finder:2.0.5--pyhdfd78af_0'
    input:
    tuple val(meta), path(fasta)
    output:
    path('original/*/*.integrons'), emit: integrons
    path('original/*/*.summary'), emit: summary
    script:
    """
    gzip -c -d ${fasta} > original.fa
    mkdir original
    integron_finder --cpu ${task.cpus} --linear --outdir original original.fa
    """
    stub:
    """
    mkdir -p original/stub
    touch original/stub/reference.integrons original/stub/reference.summary
    """
}
workflow INTEGRONFINDER_RUNTIME_TEST {
    take:
    sequence
    main:
    def helper = Channel.value(file("${moduleDir}/../../../../bin/integronfinder_runtime_resources.py",checkIfExists:true))
    def topology = Channel.value(file("${moduleDir}/../../../../bin/integronfinder_topology.py",checkIfExists:true))
    ORIGINAL_LINEAR_REFERENCE(sequence)
    INTEGRONFINDER_RESOURCE_PROBE(sequence,helper,topology)
    def identity=INTEGRONFINDER_RESOURCE_PROBE.out.identity.map { meta,receipt -> integronfinderResourceRecord(meta,receipt) }
    INTEGRONFINDER(sequence.join(identity,failOnDuplicate:true,failOnMismatch:true),helper,topology)
    emit:
    gbk = INTEGRONFINDER.out.gbk
    integrons = INTEGRONFINDER.out.integrons
    summary = INTEGRONFINDER.out.summary
    out = INTEGRONFINDER.out.out
    versions_integronfinder = INTEGRONFINDER.out.versions_integronfinder
    original_integrons = ORIGINAL_LINEAR_REFERENCE.out.integrons
    original_summary = ORIGINAL_LINEAR_REFERENCE.out.summary
}
