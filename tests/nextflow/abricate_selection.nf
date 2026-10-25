nextflow.enable.dsl = 2
include { PLASMID_DOWNSTREAM } from '../../subworkflows/plasmid_downstream'
workflow {
    def root = file(params.fixture_dir)
    ch_plasmids = params.empty_plasmids ? Channel.empty() : Channel.fromList(['S.2','S1'].collect { id ->
        tuple([id:id],file("${root}/${id}.fasta",checkIfExists:true))
    })
    PLASMID_DOWNSTREAM(ch_plasmids,Channel.empty(),Channel.empty(),Channel.empty(),Channel.empty(),Channel.empty())
}
