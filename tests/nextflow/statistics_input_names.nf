nextflow.enable.dsl=2
include { DESEQ2 } from '../../modules/cross_sample/deseq2'
include { DIFFERENTIAL_ABUNDANCE } from '../../modules/cross_sample/differential'
include { DIVERSITY } from '../../modules/cross_sample/diversity'
include { NETWORK_PREPARE } from '../../modules/cross_sample/network_prepare'
workflow {
    def assets = [file("${params.code_dir}/${params.program}",checkIfExists:true),
                  file("${params.code_dir}/statistics_input_contract.R",checkIfExists:true)]
    if (params.test_tool == 'deseq')
        DESEQ2(file(params.abundance,checkIfExists:true),file(params.metadata,checkIfExists:true),assets)
    else if (params.test_tool == 'internal')
        DIFFERENTIAL_ABUNDANCE(file(params.abundance,checkIfExists:true),file(params.metadata,checkIfExists:true),assets)
    else if (params.test_tool == 'diversity')
        DIVERSITY(file(params.abundance,checkIfExists:true),file(params.metadata,checkIfExists:true),assets)
    else
        NETWORK_PREPARE(file(params.abundance,checkIfExists:true),file(params.metadata,checkIfExists:true),assets)
}
