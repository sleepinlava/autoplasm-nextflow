nextflow.enable.dsl=2

include { MACSYFINDER_SEARCH as CONJSCAN } from '../../modules/nf-core/macsyfinder/search/main'

workflow {
    proteins=Channel.value(tuple([id:'boundary'],file(params.proteins,checkIfExists:true),file(params.topology,checkIfExists:true)))
    CONJSCAN(proteins,Channel.value(file(params.models,checkIfExists:true)),'CONJScan/Plasmids all')
}
