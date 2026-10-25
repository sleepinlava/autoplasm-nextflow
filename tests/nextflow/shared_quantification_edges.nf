nextflow.enable.dsl=2
include { SHARED_QUANTIFICATION } from '../../subworkflows/shared_quantification'

workflow {
    assemblies = Channel.fromList(['A', 'B', 'C', 'D']).map { sid ->
        tuple([id: sid, single_end: false], file("${params.fixture_dir}/${sid}/assembly.fasta", checkIfExists: true))
    }
    candidates = Channel.fromList(['D', 'C', 'B', 'A']).map { sid ->
        tuple([id: sid, single_end: false], file("${params.fixture_dir}/${sid}/plasmids.fasta", checkIfExists: true))
    }
    reads = Channel.fromList(params.read_ids).map { sid ->
        tuple([id: sid, single_end: false], file("${params.fixture_dir}/${sid}/R1.fastq"), file("${params.fixture_dir}/${sid}/R2.fastq"))
    }
    SHARED_QUANTIFICATION(assemblies, candidates, reads, Channel.empty(), 'short', 4)
}
