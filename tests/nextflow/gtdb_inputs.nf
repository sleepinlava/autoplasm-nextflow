nextflow.enable.dsl=2
include { resourceInput; taggedResourceInput } from '../../lib/resource_inputs'

include { GTDBTK_CLASSIFYWF as GTDBTK } from '../../modules/nf-core/gtdbtk/classifywf/main'

workflow {
    inputs = Channel.fromList(params.records).map { row ->
        tuple([id: row.id],row.bins.collect { file(it,checkIfExists:true) })
    }
    GTDBTK(inputs,Channel.value(taggedResourceInput([id:'EXPLICIT_INTERFACE_FIXTURE'], params.gtdbtk_db)),false, Channel.value(file("${moduleDir}/../../bin/normalize_gtdb_bins.py", checkIfExists: true)))
}
