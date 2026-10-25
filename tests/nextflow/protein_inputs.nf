nextflow.enable.dsl=2

include { PLASMID_DOWNSTREAM } from '../../subworkflows/plasmid_downstream'

workflow {
    plasmids = Channel.fromList(params.records).map { row -> tuple([id:row.id],file(row.fasta,checkIfExists:true)) }
    PLASMID_DOWNSTREAM(plasmids,Channel.empty(),Channel.empty(),Channel.empty(),Channel.empty(),Channel.empty())
    PLASMID_DOWNSTREAM.out.report_events.view { value -> 'PROTEIN_AUDIT_EVENT '+groovy.json.JsonOutput.toJson(value) }
}
