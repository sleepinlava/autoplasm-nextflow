// No reads are mapped for a globally empty reference, but all cohort members
// must remain represented in the production quantification and report events.
include { SHARED_QUANTIFICATION } from '../../subworkflows/shared_quantification'
include { REPORTING } from '../../modules/cross_sample/report'
include { reportSamples } from '../../lib/report_events'

workflow {
    ids = ['001', '1', 'NA']
    fasta = Channel.fromList(ids).map { sid ->
        tuple([id:sid], file("${params.fixture_dir}/${sid}/plasmids.fasta", checkIfExists:true))
    }
    SHARED_QUANTIFICATION(fasta, fasta, Channel.empty(), Channel.empty(), 'short', ids.size())
    consensus = Channel.fromList(ids).map { sid ->
        tuple([id:sid], file("${params.fixture_dir}/${sid}/consensus.tsv", checkIfExists:true))
    }
    structure = Channel.fromList(ids).map { sid ->
        tuple([id:sid], file("${params.fixture_dir}/${sid}/structure.tsv", checkIfExists:true))
    }
    events = SHARED_QUANTIFICATION.out.report_events.mix(
        reportSamples(fasta, 'plasmid_fasta', 'controlled_empty'),
        reportSamples(consensus, 'consensus', 'controlled_empty'),
        reportSamples(structure, 'structure', 'controlled_empty'))
    REPORTING(events, file("${params.fixture_dir}/samples.tsv", checkIfExists:true),
        [platform:'illumina', project_name:'Empty reference provenance technical control'])
}
