nextflow.enable.dsl=2
include { ABRICATE_RUN; ABRICATE_RESOURCE_PROBE } from '../main'
include { abricateResourceRecord } from '../../../../../lib/abricate_runtime'
workflow ABRICATE_RUNTIME_TEST {
    take:
    sequence
    database
    main:
    def helper = Channel.value(file("${moduleDir}/../../../../../bin/abricate_runtime_resources.pl",checkIfExists:true))
    ABRICATE_RESOURCE_PROBE(sequence,database,helper)
    def identity = ABRICATE_RESOURCE_PROBE.out.identity.map { meta, receipt -> abricateResourceRecord(meta,receipt) }
    ABRICATE_RUN(sequence.join(identity,failOnDuplicate:true,failOnMismatch:true),database,helper)
    emit:
    report = ABRICATE_RUN.out.report
    versions_abricate = ABRICATE_RUN.out.versions_abricate
}
