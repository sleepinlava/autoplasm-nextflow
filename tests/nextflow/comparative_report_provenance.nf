include { COMPARATIVE } from '../../subworkflows/comparative'
include { REPORTING } from '../../modules/cross_sample/report'
include { reportSamples } from '../../lib/report_events'

workflow {
    ids = ['001', '1', 'NA']
    fasta = Channel.fromList(ids).map { sid ->
        tuple([id:sid], file("${params.fixture_dir}/${sid}.plasmid_contigs.fasta", checkIfExists:true))
    }
    COMPARATIVE(fasta, Channel.empty())
    consensus = Channel.fromList(ids).map { sid ->
        tuple([id:sid], file("${params.fixture_dir}/${sid}.consensus.tsv", checkIfExists:true))
    }
    structure = Channel.fromList(ids).map { sid ->
        tuple([id:sid], file("${params.fixture_dir}/${sid}.structure.tsv", checkIfExists:true))
    }
    events = COMPARATIVE.out.report_events.mix(
        reportSamples(fasta, 'plasmid_fasta', 'controlled_detection'),
        reportSamples(consensus, 'consensus', 'controlled_detection'),
        reportSamples(structure, 'structure', 'controlled_detection'))
    REPORTING(events, file("${params.fixture_dir}/samples.tsv", checkIfExists:true),
        [platform:'assembly', project_name:'Comparative cohort provenance technical control'])
}
