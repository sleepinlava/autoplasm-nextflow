nextflow.enable.dsl = 2

include { MERGE_ABUNDANCE as MERGE_ABUNDANCE_FOR_LINK } from '../../modules/cross_sample/merge_abundance'
include { LINK_COABUNDANCE } from '../../modules/linking/coabundance'

workflow {
    def root = file(params.fixture_dir)
    // Deliberately send samples in an order different from lexical/sample-name order.
    def ids = ['A__B.v1', 'S.2', 'S.1']
    ch_abundance = Channel.fromList(ids.collect { id ->
        tuple([id: id], file("${root}/${id}.coverm.tsv", checkIfExists: true))
    })
    ch_profiles = Channel.fromList(ids.collect { id ->
        tuple([id: id], file("${root}/${id}.metaphlan.tsv", checkIfExists: true))
    })
    ch_abundance_input = ch_abundance.toList().map { entries ->
        tuple(entries.collect { entry -> entry[0].id }, entries.collect { entry -> entry[1] })
    }
    ch_profile_input = ch_profiles.toList().map { entries ->
        tuple(entries.collect { entry -> entry[0].id }, entries.collect { entry -> entry[1] })
    }
    MERGE_ABUNDANCE_FOR_LINK(ch_abundance_input, 'coabundance_plasmid_abundance', 'plasmid_id')
    LINK_COABUNDANCE(MERGE_ABUNDANCE_FOR_LINK.out.table, ch_profile_input)
    LINK_COABUNDANCE.out.links.view { "COABUNDANCE\t${it}" }
}
