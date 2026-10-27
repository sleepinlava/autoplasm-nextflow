nextflow.enable.dsl=2
include { PLASMIDFINDER } from '../../modules/nf-core/plasmidfinder'
workflow {
    PLASMIDFINDER(Channel.value(tuple([id:'positive',single_end:false],file(params.fasta,checkIfExists:true))))
}
