nextflow.enable.dsl=2
include { isescanResourceRecord } from '../../lib/isescan_runtime'
include { ISESCAN; ISESCAN_RESOURCE_PROBE } from '../../modules/annotation/isescan'

workflow {
    def sequence = Channel.value(tuple([id:'S.1', group:'FIXED_SOFTWARE_FIXTURE'],file(params.fasta,checkIfExists:true)))
    def helper = Channel.value(file("${moduleDir}/../../bin/isescan_runtime_resources.py",checkIfExists:true))
    ISESCAN_RESOURCE_PROBE(sequence,helper)
    def identity = ISESCAN_RESOURCE_PROBE.out.identity.map { meta,receipt -> isescanResourceRecord(meta,receipt) }
    ISESCAN(sequence.join(identity,failOnDuplicate:true,failOnMismatch:true),helper)
    ISESCAN.out.results.view { meta, result -> 'ISESCAN_RESULT=' + groovy.json.JsonOutput.toJson([meta:meta,directory:result.toString()]) }
}
