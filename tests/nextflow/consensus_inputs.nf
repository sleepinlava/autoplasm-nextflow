nextflow.enable.dsl=2

include { PLASMID_CONSENSUS } from '../../modules/detection/consensus'
include { PLASMID_STRUCTURE } from '../../modules/detection/structure'

workflow {
    inputs = Channel.fromList(params.ids.split(',').toList()).map { sid ->
        def base = "${params.fixture_dir}/${sid}"
        def extra = file("${base}.platon.tsv")
        def plasx = file("${base}.plasx.tsv")
        def legacy = file("${base}.scapp.fasta")
        def extras = extra.exists() ? [extra] : (plasx.exists() ? [plasx] : (legacy.exists() ? [legacy] : []))
        tuple([id: sid], file("${base}.assembly.fa", checkIfExists: true),
              file("${base}.genomad.tsv", checkIfExists: true), extras)
    }
    PLASMID_CONSENSUS(inputs)
    PLASMID_STRUCTURE(PLASMID_CONSENSUS.out.contigs)
}
