nextflow.enable.dsl=2
include { PLATON } from '../../modules/detection/platon'
workflow {
    candidates=Channel.fromList(params.records).map { row -> tuple([id:row.id,group:'preserved'],file(row.fasta,checkIfExists:true)) }
    PLATON(candidates,Channel.value(tuple(file(params.database,checkIfExists:true),
        files("${params.database}/**",type:'file',hidden:true))), Channel.value(file("${moduleDir}/../../bin/platon_checked.py", checkIfExists: true)))
    PLATON.out.predictions.view { meta, value -> 'PLATON_PRODUCT='+meta.id+':'+value }
}
