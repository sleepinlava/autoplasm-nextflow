nextflow.enable.dsl=2

// Pilot only: test config places both processes in the same fixed native prefix.
process SEMIBIN_RESOURCE_PROBE {
    cache false
    input:
    path probe, stageAs: 'resource_probe.py'
    output:
    path 'resource_identity.json'
    script:
    """
    python resource_probe.py --output resource_identity.json
    """
}

include { SEMIBIN_SINGLEEASYBIN as SEMIBIN } from './semibin_runtime_consumer'

workflow {
    def probe = file(params.probe, checkIfExists:true)
    SEMIBIN_RESOURCE_PROBE(Channel.value(probe))
    SEMIBIN(Channel.value(tuple([id:'sample'], file(params.fasta,checkIfExists:true),
                               file(params.bam,checkIfExists:true))),
            Channel.value(file(params.state_helper,checkIfExists:true)),
            SEMIBIN_RESOURCE_PROBE.out,
            Channel.value(probe))
}
