nextflow.enable.dsl=2
include { OPERA_MS } from '../../modules/assembly/opera_ms'

workflow {
    OPERA_MS(Channel.of(tuple([id:params.sample_id],
        file(params.read1, checkIfExists:true),
        file(params.read2, checkIfExists:true),
        file(params.long_reads, checkIfExists:true))), Channel.value(file("${moduleDir}/../../bin/validate_opera_ms_output.py", checkIfExists: true)))
}
