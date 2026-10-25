nextflow.enable.dsl=2

include { GTDBTK_CLASSIFYWF as GTDBTK } from '../../modules/nf-core/gtdbtk/classifywf/main'

workflow {
    inputs = Channel.fromList(params.records).map { row ->
        tuple([id: row.id],row.bins.collect { file(it,checkIfExists:true) })
    }
    GTDBTK(inputs,Channel.value([[id:'EXPLICIT_INTERFACE_FIXTURE'],file(params.gtdbtk_db,checkIfExists:true)]),false, Channel.value(file("${moduleDir}/../../bin/normalize_gtdb_bins.py", checkIfExists: true)))
}
