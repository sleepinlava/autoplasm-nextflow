nextflow.enable.dsl = 2

include { HOST_LINKING } from '../../subworkflows/host_linking'
include { LINK_CRISPR } from '../../modules/linking/crispr'

workflow {
    if (params.direct_module) {
        def root = file(params.fixture_dir)
        LINK_CRISPR(Channel.of(tuple([id: 'S1'],
            file("${root}/S1.plasmid_contigs.fasta", checkIfExists: true),
            file("${root}/S1.metabat2_bins", checkIfExists: true))))
        LINK_CRISPR.out.links.view { "LINK\t${it}" }
    } else {
        HOST_LINKING(Channel.empty(), Channel.empty(), Channel.empty(), Channel.empty(),
                     Channel.empty(), Channel.empty(), Channel.empty(), false)
        HOST_LINKING.out.links.view { "LINK\t${it}" }
    }
}
