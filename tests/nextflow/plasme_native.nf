nextflow.enable.dsl=2
include { PLASME } from '../../modules/detection/plasme'

workflow {
    PLASME(Channel.of(tuple([id:params.sample_id],file(params.assembly,checkIfExists:true))),
           Channel.value(file(params.database,checkIfExists:true)),
           Channel.value(file(params.source_dir,checkIfExists:true)), Channel.value(tuple(file("${moduleDir}/../../bin/normalize_plasme_outputs.py", checkIfExists: true), file("${moduleDir}/../../bin/plasme_runtime.py", checkIfExists: true))))
}
