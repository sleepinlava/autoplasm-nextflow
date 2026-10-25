include { selectedTools } from '../lib/tool_selection'
include { reportEvidence } from '../lib/report_events'
include { GPLAS2_NODES; GPLAS2_PREDICTIONS } from '../modules/binning/gplas_inputs'
include { GPLAS2 } from '../modules/binning/gplas2'
include { PLASMID_DETECTION as GPLAS_NODE_DETECTION } from './plasmid_detection'

workflow GPLAS_BINNING {
    take:
    ch_assembly // all full assemblies: establishes expected sample set, never only positive contigs
    ch_graph    // same-task SPAdes GFA segments, including KC counts

    main:
    ch_events = Channel.empty()
    ch_bins = Channel.empty()
    ch_states = Channel.empty()
    if (selectedTools(params.plasmid_binning_tools).contains('gplas2')) {
        ch_expected_graphs = ch_assembly.map { meta, fasta -> tuple(meta.id.toString(), meta) }
            .join(ch_graph.map { meta, graph -> tuple(meta.id.toString(), meta, graph) },
                  failOnDuplicate: true, failOnMismatch: true)
            .map { sampleId, meta, graphMeta, graph ->
                if (meta != graphMeta) error("gplas graph metadata differs from assembly sample ${sampleId}")
                // This namespace prevents node classifiers from overwriting
                // assembled-contig outputs even when local IDs happen to match.
                def digest = java.security.MessageDigest.getInstance('SHA-256')
                    .digest(meta.id.toString().getBytes('UTF-8')).encodeHex().toString()
                tuple(meta + [id: "gplas_nodes_${digest}", gplas_original_meta: meta,
                              analysis_entity: 'gplas_graph_node'], graph)
            }
        GPLAS2_NODES(ch_expected_graphs, Channel.value(file("${moduleDir}/../bin/gplas_inputs.py", checkIfExists: true)))
        ch_nodes = GPLAS2_NODES.out.nodes.filter { meta, graph, nodes -> nodes.size() > 0 }
        // Same selected classifiers, weights and consensus strategy; only the
        // approved analysis entity changes from assembly contigs to GFA nodes.
        GPLAS_NODE_DETECTION(ch_nodes.map { meta, graph, nodes -> tuple(meta, nodes) })
        ch_assessment = GPLAS_NODE_DETECTION.out.aggregated_classification.map { meta, paths ->
            def tables = paths in List ? paths : [paths]
            // Provirus tables can accompany the original sequence table.
            // Select the exact original-node filename, never the first match.
            def expected = "${meta.id}.gplas_nodes_aggregated_classification.tsv"
            def matching = tables.findAll { it.name == expected }
            if (matching.size() != 1) error("Expected one original-node geNomad assessment table: ${expected}")
            tuple(meta, matching[0])
        }
        GPLAS2_PREDICTIONS(ch_nodes.map { meta, graph, nodes -> tuple(meta, graph) }
            .join(GPLAS_NODE_DETECTION.out.consensus, failOnDuplicate: true, failOnMismatch: true)
            .join(ch_assessment, failOnDuplicate: true, failOnMismatch: true), Channel.value(file("${moduleDir}/../bin/gplas_inputs.py", checkIfExists: true)))
        GPLAS2(GPLAS2_PREDICTIONS.out.ready,
            Channel.value(tuple(file(params.gplas_source, checkIfExists: true),
                files("${params.gplas_source}/**", type: 'file', hidden: true))), Channel.value(file("${moduleDir}/../bin/gplas_checked.py", checkIfExists: true)))
        ch_bins = GPLAS2.out.bins.map { meta, bins -> tuple(meta.gplas_original_meta, bins) }
        ch_states = GPLAS2_NODES.out.state.mix(GPLAS2_PREDICTIONS.out.state)
            .map { meta, state -> tuple(meta.gplas_original_meta, state) }
        ch_events = ch_events.mix(
            reportEvidence([channels: GPLAS2_NODES.out], '05_plasmid_binning', 'GPLAS2_NODES'),
            reportEvidence([channels: GPLAS2_PREDICTIONS.out], '05_plasmid_binning', 'GPLAS2_PREDICTIONS'),
            reportEvidence([channels: GPLAS2.out], '05_plasmid_binning', 'GPLAS2'))
        // Preserve node-tool completion evidence without adding graph nodes to
        // the report's assembled-contig/plasmid sample counters.
        ch_events = ch_events.mix(GPLAS_NODE_DETECTION.out.report_events
            .filter { event, files -> event.kind == 'evidence' }
            .map { event, files -> tuple(event + [section: '05_plasmid_binning', analysis_entity: 'graph_node'], files) })
    }

    emit:
    bins = ch_bins
    states = ch_states
    report_events = ch_events
}
