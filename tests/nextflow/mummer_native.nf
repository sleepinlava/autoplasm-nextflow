nextflow.enable.dsl=2
include { MUMMER } from '../../modules/comparative/mummer'

workflow {
    MUMMER(Channel.of(tuple([id: params.sample_id], file(params.query, checkIfExists: true))),
           Channel.value(file(params.reference, checkIfExists: true)))
}
