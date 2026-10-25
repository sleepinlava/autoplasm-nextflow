nextflow.enable.dsl=2
include { DESEQ2 } from '../../modules/cross_sample/deseq2'
workflow {
    DESEQ2(file(params.abundance, checkIfExists:true), file(params.metadata, checkIfExists:true),
        [file("${params.code_dir}/deseq2_plasmid.R",checkIfExists:true),
         file("${params.code_dir}/statistics_input_contract.R",checkIfExists:true)])
}
