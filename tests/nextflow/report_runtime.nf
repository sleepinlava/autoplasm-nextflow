nextflow.enable.dsl=2
include { PLASMID_CONSENSUS } from '../../modules/detection/consensus'
include { PLASMID_CONSENSUS as GRAPH_CONSENSUS } from '../../modules/detection/consensus'
include { PLASMID_STRUCTURE } from '../../modules/detection/structure'
include { REPORTING } from '../../modules/cross_sample/report'
include { reportEvidence; reportSamples } from '../../lib/report_events'

workflow {
    // Explicit controlled predictions; real R algorithms/report, no classifier inference.
    inputs = Channel.fromList(['S.1','001']).map { sid ->
        tuple([id:sid], file("${params.fixture_dir}/${sid}.fasta", checkIfExists:true),
              file("${params.fixture_dir}/${sid}.summary.tsv", checkIfExists:true), [])
    }
    PLASMID_CONSENSUS(inputs)
    PLASMID_STRUCTURE(PLASMID_CONSENSUS.out.contigs)
    GRAPH_CONSENSUS(Channel.value(tuple(
        [id:'gplas_nodes_control_001',analysis_entity:'gplas_graph_node',gplas_original_meta:[id:'001']],
        file("${params.fixture_dir}/001.fasta", checkIfExists:true),
        file("${params.fixture_dir}/001.summary.tsv", checkIfExists:true), [])))
    events = reportEvidence([channels:PLASMID_CONSENSUS.out], '04_plasmid_detection', 'PLASMID_CONSENSUS')
        .mix(reportEvidence([channels:PLASMID_STRUCTURE.out], '04_plasmid_detection', 'PLASMID_STRUCTURE'),
             reportEvidence([channels:GRAPH_CONSENSUS.out], '04_plasmid_detection', 'GRAPH_CONSENSUS'),
             reportSamples(PLASMID_CONSENSUS.out.contigs, 'plasmid_fasta', 'PLASMID_CONSENSUS'),
             reportSamples(PLASMID_CONSENSUS.out.consensus, 'consensus', 'PLASMID_CONSENSUS'),
             reportSamples(PLASMID_STRUCTURE.out.structure, 'structure', 'PLASMID_STRUCTURE'))
    REPORTING(events, file("${params.fixture_dir}/samples.tsv",checkIfExists:true),
              [platform:'assembly',project_name:'Native R provenance controls'])
}
