nextflow.enable.dsl=2
include { plasmidfinderResourceRecord } from '../../lib/plasmidfinder_runtime'
include { PLASMIDFINDER; PLASMIDFINDER_RESOURCE_PROBE } from '../../modules/nf-core/plasmidfinder'
workflow {
    def sequence=Channel.value(tuple([id:'positive',single_end:false],file(params.fasta,checkIfExists:true)))
    def helper=Channel.value(file("${moduleDir}/../../bin/plasmidfinder_runtime_resources.py",checkIfExists:true))
    PLASMIDFINDER_RESOURCE_PROBE(sequence,helper)
    def identity=PLASMIDFINDER_RESOURCE_PROBE.out.identity.map { meta,receipt -> plasmidfinderResourceRecord(meta,receipt) }
    PLASMIDFINDER(sequence.join(identity,failOnDuplicate:true,failOnMismatch:true),helper)
}
