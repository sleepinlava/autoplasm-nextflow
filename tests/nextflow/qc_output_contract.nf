nextflow.enable.dsl=2
include { FASTP } from '../../modules/nf-core/fastp'
include { INTEGRONFINDER } from '../../modules/nf-core/integronfinder'

workflow {
    if (params.contract_tool == 'fastp') {
        FASTP(Channel.of(tuple([id:'sample', single_end:params.input_mode != 'pe'],
            params.reads.collect { file(it, checkIfExists:true) }, [])), false, false, false)
        FASTP.out.reads.toList().map { rows ->
            groovy.json.JsonOutput.toJson(rows.collect { meta, reads ->
                [id:meta.id, files:(reads instanceof List ? reads : [reads]).collect { it.toString() }]
            })
        }.collectFile(name:'reads-channel.json', storeDir:params.observe_dir)
    } else if (params.contract_tool == 'integronfinder') {
        INTEGRONFINDER(Channel.of(tuple([id:'sample'], file(params.fasta, checkIfExists:true))))
        INTEGRONFINDER.out.gbk.toList().map { rows ->
            groovy.json.JsonOutput.toJson(rows.collect { meta, files ->
                [id:meta.id, files:(files instanceof List ? files : [files]).collect { it.toString() }]
            })
        }.collectFile(name:'gbk-channel.json', storeDir:params.observe_dir)
    } else {
        error "Unknown contract_tool: ${params.contract_tool}"
    }
}
