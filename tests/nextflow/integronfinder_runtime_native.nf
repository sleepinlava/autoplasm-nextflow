nextflow.enable.dsl=2
include { integronfinderResourceRecord } from '../../lib/integronfinder_runtime'
include { INTEGRONFINDER; INTEGRONFINDER_RESOURCE_PROBE } from '../../modules/nf-core/integronfinder'
workflow {
    def sequence = Channel.value(tuple([id:'sample'],file(params.fasta,checkIfExists:true)))
    def helper = Channel.value(file("${moduleDir}/../../bin/integronfinder_runtime_resources.py",checkIfExists:true))
    def topology = Channel.value(file("${moduleDir}/../../bin/integronfinder_topology.py",checkIfExists:true))
    INTEGRONFINDER_RESOURCE_PROBE(sequence,helper,topology)
    def identity=INTEGRONFINDER_RESOURCE_PROBE.out.identity.map { meta,receipt -> integronfinderResourceRecord(meta,receipt) }
    INTEGRONFINDER(sequence.join(identity,failOnDuplicate:true,failOnMismatch:true),helper,topology)
}
