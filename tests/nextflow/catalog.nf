nextflow.enable.dsl = 2

include { PLASMID_CATALOG_PREPARE as PLASMID_CATALOG_PREPARE_DIRECT } from '../../modules/comparative/catalog_prepare'
include { COMPARATIVE } from '../../subworkflows/comparative'

workflow {
    if (params.test_comparative_empty) {
        COMPARATIVE(Channel.empty(), Channel.empty())
    } else {
        ch_catalog_files = Channel
            .fromPath("${params.fixture_dir}/*.plasmid_contigs.fasta", checkIfExists: false)
            .collect()
            .filter { files -> !files.isEmpty() }
        PLASMID_CATALOG_PREPARE_DIRECT(ch_catalog_files)
        PLASMID_CATALOG_PREPARE_DIRECT.out.combined.view { "CATALOG\t${it}" }
    }
}
