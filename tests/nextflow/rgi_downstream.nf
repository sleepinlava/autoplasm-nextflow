nextflow.enable.dsl=2

include { PLASMID_DOWNSTREAM } from '../../subworkflows/plasmid_downstream'

workflow {
    candidates = Channel.fromList(params.records).map { row -> tuple([id: row.id], file(row.fasta, checkIfExists: true)) }
    PLASMID_DOWNSTREAM(candidates, Channel.empty(), Channel.empty(), Channel.empty(), Channel.empty(), Channel.empty())
}
