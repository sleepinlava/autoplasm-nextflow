nextflow.enable.dsl=2
include { resourceInput } from '../../lib/resource_inputs'

include { MACSYFINDER_SEARCH as CONJSCAN } from '../../modules/nf-core/macsyfinder/search/main'

workflow {
    proteins=Channel.value(tuple([id:'boundary'],file(params.proteins,checkIfExists:true),file(params.topology,checkIfExists:true)))
    CONJSCAN(proteins,Channel.value(resourceInput(params.models)),'CONJScan/Plasmids all')
}
