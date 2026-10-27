nextflow.enable.dsl=2
include { SEMIBIN_SINGLEEASYBIN as SEMIBIN; SEMIBIN_RESOURCE_PROBE } from '../main'
include { semibinResourceRecord } from '../../../../../lib/semibin_runtime'

workflow SEMIBIN_RUNTIME_TEST {
    take:
    sequence
    state_helper
    resource_helper
    main:
    SEMIBIN_RESOURCE_PROBE(sequence, resource_helper)
    def identity = SEMIBIN_RESOURCE_PROBE.out.identity.map { meta, receipt -> semibinResourceRecord(meta, receipt) }
    SEMIBIN(sequence.join(identity, failOnDuplicate:true, failOnMismatch:true), state_helper, resource_helper)
    emit:
    source_fasta = sequence.map { meta, fasta, bam -> tuple(meta, fasta) }
    csv = SEMIBIN.out.csv
    model = SEMIBIN.out.model
    tsv = SEMIBIN.out.tsv
    output_fasta = SEMIBIN.out.output_fasta
    state = SEMIBIN.out.state
    versions_semibin = SEMIBIN.out.versions_semibin
    versions_cuda = SEMIBIN.out.versions_cuda
}
