// Native technical controls: exercise aliases inside a named workflow, then
// consume their actual output events through the production report builder.
include { NETWORK_PREPARE as NETWORK_ALIAS } from '../../modules/cross_sample/network_prepare'
include { reportEvidence; reportSamples } from '../../lib/report_events'
include { REPORTING } from '../../modules/cross_sample/report'

workflow COHORT_REVIEW {
    take:
    fixture_dir
    main:
    NETWORK_ALIAS(file("${fixture_dir}/abundance.tsv", checkIfExists:true),
        file("${fixture_dir}/samples.tsv", checkIfExists:true),
        ['network_prepare.R', 'statistics_input_contract.R'].collect {
            file("${projectDir}/../../bin/${it}", checkIfExists:true)
        })
    events = reportEvidence([channels:NETWORK_ALIAS.out], '12_network', 'NETWORK_ALIAS')
    ['plasmid_fasta':'plasmids.fasta', 'consensus':'consensus.tsv', 'structure':'structure.tsv'].each { kind, name ->
        def sources = Channel.fromList(['001', '1', 'NA']).map { sid ->
            tuple([id:sid], file("${fixture_dir}/${sid}/${name}", checkIfExists:true))
        }
        events = events.mix(reportSamples(sources, kind, 'controlled_detection'))
    }
    REPORTING(events, file("${fixture_dir}/samples.tsv", checkIfExists:true),
        [platform:'illumina', project_name:'Nested cohort provenance technical control'])
}

workflow {
    COHORT_REVIEW(params.fixture_dir)
}
