nextflow.enable.dsl=2
include { COPLA } from '../../modules/typing/copla'

workflow {
    COPLA(Channel.of(tuple([id:params.sample_id], file(params.assembly,checkIfExists:true))),
          Channel.value(file(params.refgraph,checkIfExists:true)),
          Channel.value(file(params.reflist,checkIfExists:true)),
          Channel.value(file(params.installation,checkIfExists:true)),
          Channel.value(file(params.macsyfinder,checkIfExists:true)), Channel.value(file("${moduleDir}/../../bin/run_copla_candidates.py", checkIfExists: true)))
}
