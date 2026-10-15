nextflow.enable.dsl = 2

include { HOST_LINKING } from '../../subworkflows/host_linking'

params.host_plasmid_linking = true
params.host_linking_methods = ['long_read']
params.host_linking_optional_methods = []

workflow {
    def root = file(params.fixture_dir)
    def meta = [id: 'S1']
    ch_plasmids = Channel.of(tuple(meta, file("${root}/S1.plasmid_contigs.fasta", checkIfExists: true)))
    ch_assembly = Channel.of(tuple(meta, file("${root}/S1.assembly.fasta", checkIfExists: true)))
    ch_longread_bam = Channel.of(tuple(meta, file("${root}/S1.long.bam", checkIfExists: true)))
    HOST_LINKING(ch_plasmids, ch_assembly, ch_longread_bam, Channel.empty(),
                 Channel.empty(), Channel.empty(), Channel.empty(), true)
    HOST_LINKING.out.links.view { "LONGREAD_LINK\t${it}" }
}
