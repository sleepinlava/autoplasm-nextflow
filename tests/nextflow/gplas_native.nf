nextflow.enable.dsl=2
include { GPLAS2 } from '../../modules/binning/gplas2'
workflow {
    records = Channel.fromList(params.records).map { row ->
        tuple([id: "native_graph_${row.id}", gplas_original_meta: [id: row.id, group: 'preserved']],
            file(row.graph, checkIfExists: true), file(row.predictions, checkIfExists: true),
            file(params.ready_marker, checkIfExists: true))
    }
    GPLAS2(records, Channel.value(tuple(file(params.gplas_source, checkIfExists: true),
        files("${params.gplas_source}/**", type: 'file', hidden: true))), Channel.value(file("${moduleDir}/../../bin/gplas_checked.py", checkIfExists: true)))
    GPLAS2.out.bins.view { meta, result -> "GPLAS_PRODUCT=${meta.gplas_original_meta.id}:${result}" }
}
