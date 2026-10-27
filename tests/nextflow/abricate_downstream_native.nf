nextflow.enable.dsl=2
include { PLASMID_DOWNSTREAM } from '../../subworkflows/plasmid_downstream'
workflow {
    def sequence = params.empty_input ? Channel.empty() : Channel.value(tuple([id:'S.1',platform:'assembly'],file(params.fasta,checkIfExists:true)))
    PLASMID_DOWNSTREAM(sequence,Channel.empty(),Channel.empty(),Channel.empty(),Channel.empty(),Channel.empty())
    PLASMID_DOWNSTREAM.out.report_events.collect(flat:false).ifEmpty([]).map { events ->
        file(params.events).text = groovy.json.JsonOutput.toJson(events)
        events.size()
    }.view()
}
