nextflow.enable.dsl=2
include { GPLAS_BINNING } from '../../subworkflows/gplas_binning'
workflow {
    // Copy ConfigMap records and never use Groovy Map.get(key, default), which inserts missing keys.
    def records = params.records.collect { new LinkedHashMap(it) }
    assemblies = Channel.fromList(records).map { row -> tuple([id: row.id, group: 'preserved'], file(row.assembly, checkIfExists: true)) }
    graphs = Channel.fromList(records.findAll { it.graph }).map { row -> tuple([id: row.getOrDefault('graph_id', row.id), group: row.getOrDefault('graph_group', 'preserved')], file(row.graph, checkIfExists: true)) }
    GPLAS_BINNING(assemblies, graphs)
    GPLAS_BINNING.out.bins.view { meta, result -> "GRAPH_BIN=${meta.id}:${result}" }
    GPLAS_BINNING.out.states.view { meta, state -> "GRAPH_STATE=${meta.id}:${state}" }
    GPLAS_BINNING.out.report_events.view { event, files -> "GRAPH_EVENT=${event.kind}:${event.section}" }
}
