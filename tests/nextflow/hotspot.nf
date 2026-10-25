nextflow.enable.dsl=2

include { HOST_LINKING } from '../../subworkflows/host_linking'

workflow {
    candidates=Channel.fromList(params.records).map { row -> tuple([id:row.id],file(row.fasta,checkIfExists:true)) }
    HOST_LINKING(candidates,Channel.empty(),Channel.empty(),Channel.empty(),Channel.empty(),Channel.empty(),Channel.empty(),false)
    HOST_LINKING.out.links.view { value -> 'HOTSPOT_LINK='+value }
}
