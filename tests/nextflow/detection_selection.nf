nextflow.enable.dsl=2

include { PLASMID_DETECTION } from '../../subworkflows/plasmid_detection'

workflow {
    assemblies = Channel.fromList(['S1', 'S.2']).map { sid ->
        tuple([id: sid], file("${params.fixture_dir}/${sid}.fasta", checkIfExists: true))
    }
    PLASMID_DETECTION(assemblies)
}
