nextflow.enable.dsl=2
include { PLASMID_DOWNSTREAM } from '../../subworkflows/plasmid_downstream'

workflow {
    candidates=Channel.fromList(params.records).map { r -> tuple([id:r.id],file(r.fasta,checkIfExists:true)) }
    PLASMID_DOWNSTREAM(candidates,Channel.empty(),Channel.empty(),Channel.empty(),Channel.empty(),Channel.empty())
    PLASMID_DOWNSTREAM.out.report_events.toList().view { events -> 'COPLA_REPORT_EVENTS '+groovy.json.JsonOutput.toJson(events) }
}
