nextflow.enable.dsl=2
include { PLASMIDFINDER; PLASMIDFINDER_RESOURCE_PROBE } from '../main'
include { plasmidfinderResourceRecord } from '../../../../lib/plasmidfinder_runtime'
workflow PLASMIDFINDER_RUNTIME_TEST {
    take:
    sequence
    main:
    def helper=Channel.value(file("${moduleDir}/../../../../bin/plasmidfinder_runtime_resources.py",checkIfExists:true))
    PLASMIDFINDER_RESOURCE_PROBE(sequence,helper)
    def identity=PLASMIDFINDER_RESOURCE_PROBE.out.identity.map { meta,receipt -> plasmidfinderResourceRecord(meta,receipt) }
    PLASMIDFINDER(sequence.join(identity,failOnDuplicate:true,failOnMismatch:true),helper)
    emit:
    json=PLASMIDFINDER.out.json
    txt=PLASMIDFINDER.out.txt
    tsv=PLASMIDFINDER.out.tsv
    genome_seq=PLASMIDFINDER.out.genome_seq
    plasmid_seq=PLASMIDFINDER.out.plasmid_seq
    versions_plasmidfinder=PLASMIDFINDER.out.versions_plasmidfinder
}
