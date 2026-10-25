nextflow.enable.dsl=2
include { SHARED_QUANTIFICATION } from '../../subworkflows/shared_quantification'
include { CROSS_SAMPLE } from '../../subworkflows/cross_sample'
include { reportSamples } from '../../lib/report_events'
include { HOST_LINKING } from '../../subworkflows/host_linking'

workflow {
    ids = ['A', 'B', 'C', 'D']
    assemblies = Channel.fromList(ids.reverse()).map { sid ->
        tuple([id: sid, single_end: false], file("${params.fixture_dir}/${sid}/assembly.fasta", checkIfExists: true))
    }
    candidates = Channel.fromList(ids).map { sid ->
        tuple([id: sid, single_end: false], file("${params.fixture_dir}/${sid}/plasmids.fasta", checkIfExists: true))
    }
    short_reads = Channel.empty()
    long_reads = Channel.empty()
    if (params.read_mode == 'short') {
        short_reads = Channel.fromList(ids).map { sid ->
            tuple([id: sid, single_end: false],
                  file("${params.fixture_dir}/${sid}/R1.fastq", checkIfExists: true),
                  file("${params.fixture_dir}/${sid}/R2.fastq", checkIfExists: true))
        }
    } else {
        long_reads = Channel.fromList(ids).map { sid ->
            tuple([id: sid, single_end: false], file("${params.fixture_dir}/${sid}/long.fastq", checkIfExists: true))
        }
    }
    SHARED_QUANTIFICATION(assemblies, candidates, short_reads, long_reads, params.read_mode, 4)
    profiles = Channel.fromList(['D', 'C', 'B', 'A']).map { sid ->
        tuple([id: sid, single_end: false], file("${params.fixture_dir}/${sid}/${sid}.metaphlan.tsv", checkIfExists: true))
    }
    HOST_LINKING(Channel.empty(), Channel.empty(), Channel.empty(),
                 SHARED_QUANTIFICATION.out.plasmids, profiles, Channel.empty(), Channel.empty(), false)
    if (params.run_cross_sample) {
        report_events = SHARED_QUANTIFICATION.out.report_events.mix(HOST_LINKING.out.report_events)
        fasta_rows = Channel.fromList(['A', 'B', 'C', 'D']).map { sid -> tuple([id:sid], file("${params.fixture_dir}/${sid}/plasmids.fasta", checkIfExists:true)) }
        consensus_rows = Channel.fromList(['A', 'B', 'C', 'D']).map { sid -> tuple([id:sid], file("${params.fixture_dir}/${sid}/consensus.tsv", checkIfExists:true)) }
        structure_rows = Channel.fromList(['A', 'B', 'C', 'D']).map { sid -> tuple([id:sid], file("${params.fixture_dir}/${sid}/structure.tsv", checkIfExists:true)) }
        report_events = report_events.mix(reportSamples(fasta_rows, 'plasmid_fasta', 'controlled_detection'),
                                         reportSamples(consensus_rows, 'consensus', 'controlled_detection'),
                                         reportSamples(structure_rows, 'structure', 'controlled_detection'))
        CROSS_SAMPLE(SHARED_QUANTIFICATION.out.contigs, SHARED_QUANTIFICATION.out.plasmids, SHARED_QUANTIFICATION.out.states,
                     Channel.empty(), report_events, 4, 2)
    }
}
