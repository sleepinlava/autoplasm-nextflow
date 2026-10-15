nextflow.enable.dsl = 2

include { HOST_PROFILE_READS } from '../../subworkflows/host_prediction'

workflow {
    def fixtures = file(params.fixture_dir)
    ch_short = Channel.fromList(['S1', 'S2'].collect { id ->
        tuple([id: id], file("${fixtures}/${id}.R1.fastq", checkIfExists: true),
              file("${fixtures}/${id}.R2.fastq", checkIfExists: true))
    })
    // Hybrid deliberately supplies an empty long-read profile channel.
    HOST_PROFILE_READS(ch_short, Channel.empty())
    HOST_PROFILE_READS.out.reads.view { meta, reads -> "ROUTE\t${meta.id}\t${reads.size()}" }
}
