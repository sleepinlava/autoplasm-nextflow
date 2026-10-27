nextflow.enable.dsl=2
include { abricateResourceRecord } from '../../lib/abricate_runtime'
include { ABRICATE_RUN as ABRICATE; ABRICATE_RESOURCE_PROBE } from '../../modules/nf-core/abricate/run'
workflow {
    def sequence = Channel.value(tuple([id:'sample'],file(params.fasta,checkIfExists:true)))
    def helper = Channel.value(file("${moduleDir}/../../bin/abricate_runtime_resources.pl",checkIfExists:true))
    def database = params.datadir ? Channel.value(file(params.datadir,checkIfExists:true)) : Channel.value([])
    ABRICATE_RESOURCE_PROBE(sequence, database, helper)
    def identity = ABRICATE_RESOURCE_PROBE.out.identity.map { meta, receipt -> abricateResourceRecord(meta, receipt) }
    ABRICATE(sequence.join(identity,failOnDuplicate:true,failOnMismatch:true),database,helper)
}
