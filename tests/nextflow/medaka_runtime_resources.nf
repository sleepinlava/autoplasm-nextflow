include { MEDAKA; MEDAKA_RESOURCE_PROBE } from '../../modules/nf-core/medaka/main'
include { medakaResourceRecord } from '../../lib/medaka_runtime'

workflow {
    reads = file(params.medaka_reads,checkIfExists:true)
    assembly = file(params.medaka_assembly,checkIfExists:true)
    helpers = Channel.value(['medaka_runtime_resources.py','medaka_model_resources.py',
                             'medaka_model_selection.py','medaka_index_resources.py'].collect {
        file("${projectDir}/../../bin/${it}",checkIfExists:true)
    })
    inputs = Channel.of(tuple([id:'test',single_end:true],reads,assembly))
    MEDAKA_RESOURCE_PROBE(inputs,helpers)
    identities = MEDAKA_RESOURCE_PROBE.out.identity.map { meta,receipt -> medakaResourceRecord(meta,receipt) }
    if (params.probe_only?.toString() != 'true') {
        MEDAKA(inputs.join(identities,failOnDuplicate:true,failOnMismatch:true),helpers)
    }
}
