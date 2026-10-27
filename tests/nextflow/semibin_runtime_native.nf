nextflow.enable.dsl=2
include { semibinResourceRecord } from '../../lib/semibin_runtime'
include { SEMIBIN_SINGLEEASYBIN as SEMIBIN; SEMIBIN_RESOURCE_PROBE } from '../../modules/nf-core/semibin/singleeasybin/main'

workflow {
    def sequence = Channel.value(tuple([id:'sample'],file(params.fasta,checkIfExists:true),file(params.bam,checkIfExists:true)))
    def helper = Channel.value(file("${moduleDir}/../../bin/semibin_runtime_resources.py",checkIfExists:true))
    SEMIBIN_RESOURCE_PROBE(sequence, helper)
    def identity = SEMIBIN_RESOURCE_PROBE.out.identity.map { meta, receipt -> semibinResourceRecord(meta, receipt) }
    SEMIBIN(sequence.join(identity,failOnDuplicate:true,failOnMismatch:true),
            Channel.value(file("${moduleDir}/../../bin/semibin_output_state.py",checkIfExists:true)), helper)
}
