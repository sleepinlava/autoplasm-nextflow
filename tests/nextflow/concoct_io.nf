nextflow.enable.dsl=2

include { CONCOCT_CUTUPFASTA } from '../../modules/nf-core/concoct/cutupfasta/main'
include { CONCOCT_EXTRACTFASTABINS as CONCOCT } from '../../modules/nf-core/concoct/extractfastabins/main'

workflow {
    if (params.mode == 'cut') {
        inputs = Channel.fromList(params.records).map { row ->
            tuple([id: row.id], file(row.fasta, checkIfExists: true))
        }
        CONCOCT_CUTUPFASTA(inputs, params.bed, Channel.value(file("${moduleDir}/../../bin/run_concoct_cut_checked.py", checkIfExists: true)))
    } else if (params.mode == 'extract') {
        inputs = Channel.fromList(params.records).map { row ->
            tuple([id: row.id], file(row.fasta, checkIfExists: true), file(row.csv, checkIfExists: true))
        }
        CONCOCT(inputs)
        CONCOCT.out.fasta.view { meta, bins -> "EXTRACTED_BINS=${meta.id}:${bins}" }
    } else {
        error('Unknown CONCOCT I/O test mode')
    }
}
