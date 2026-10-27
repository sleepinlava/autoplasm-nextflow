nextflow.enable.dsl=2
include { GPLAS2 } from '../../modules/binning/gplas2'
workflow {
    def ResourceIdentity = new GroovyClassLoader().parseClass(new File("${moduleDir}/../../lib/ResourceIdentity.groovy"))
    def resource = { location ->
        def directory = file(location, checkIfExists: true)
        tuple(directory, ResourceIdentity.capture(directory))
    }
    records = Channel.fromList(params.records).map { row ->
        tuple([id: "native_graph_${row.id}", gplas_original_meta: [id: row.id, group: 'preserved']],
            file(row.graph, checkIfExists: true), file(row.predictions, checkIfExists: true),
            file(params.ready_marker, checkIfExists: true))
    }
    GPLAS2(records, Channel.value(resource.call(params.gplas_source)), Channel.value(file("${moduleDir}/../../bin/gplas_checked.py", checkIfExists: true)))
    GPLAS2.out.bins.view { meta, result -> "GPLAS_PRODUCT=${meta.gplas_original_meta.id}:${result}" }
}
