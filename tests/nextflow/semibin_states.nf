nextflow.enable.dsl=2

include { SEMIBIN_SINGLEEASYBIN as SEMIBIN } from '../../modules/nf-core/semibin/singleeasybin/main'

workflow {
    SEMIBIN(Channel.value(tuple([id:'sample'],file(params.fasta,checkIfExists:true),file(params.bam,checkIfExists:true))), Channel.value(file("${moduleDir}/../../bin/semibin_output_state.py", checkIfExists: true)))
    SEMIBIN.out.output_fasta.view { meta, bins -> 'BIN_EMIT='+meta.id }
    SEMIBIN.out.model.view { meta, model -> 'MODEL_EMIT='+meta.id }
    if (!params.original) {
        SEMIBIN.out.state.view { meta, state -> 'STATE_EMIT='+meta.id }
    }
}
