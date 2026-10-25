nextflow.enable.dsl=2
include { LINK_SEQUENCE } from '../../modules/linking/sequence'
workflow {
    samples = Channel.fromList(['P','S']).map { id ->
        def root = "${params.fixture_dir}/${id}"
        tuple([id:id,group:'preserved'], file("${root}/plasmids.fasta",checkIfExists:true),
              [file("${root}/MAG files",checkIfExists:true)],
              [file("${root}/taxonomy.tsv",checkIfExists:true), file("${root}/second-domain/taxonomy.tsv",checkIfExists:true)])
    }
    LINK_SEQUENCE(samples)
}
