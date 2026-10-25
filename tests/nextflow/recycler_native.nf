// Native contract regression using original SPADES/downstream/Recycler modules.
// Small SPAdes bundled fixtures; not a biological performance benchmark.
nextflow.enable.dsl = 2
include { SPADES } from '../../modules/nf-core/spades/main'
include { PLASMID_DOWNSTREAM } from '../../subworkflows/plasmid_downstream'

workflow {
    def root = file(params.fixture_dir)
    ch_reads = Channel.fromList([
        tuple([id:'K33'], file("${root}/test_dataset/ecoli_1K_1.fq.gz",checkIfExists:true),
                         file("${root}/test_dataset/ecoli_1K_2.fq.gz",checkIfExists:true)),
        tuple([id:'K55'], file("${root}/test_dataset_plasmid/pl1.fq.gz",checkIfExists:true),
                         file("${root}/test_dataset_plasmid/pl2.fq.gz",checkIfExists:true))
    ])
    SPADES(ch_reads.map { meta, r1, r2 -> tuple(meta, [r1,r2], [], []) }, [], [], Channel.value(file("${moduleDir}/../../bin/spades_graph_provenance.py", checkIfExists: true)))
    PLASMID_DOWNSTREAM(Channel.empty(), SPADES.out.fastg, Channel.empty(),
        Channel.empty(), ch_reads, SPADES.out.recycler_graph)
}
