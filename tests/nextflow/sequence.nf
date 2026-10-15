nextflow.enable.dsl = 2

include { LINK_SEQUENCE } from '../../modules/linking/sequence'

workflow {
    def meta = [id: params.sample_id ?: 'S1']
    def plasmid = file("${params.fixture_dir}/${meta.id}.plasmid_contigs.fasta", checkIfExists: true)
    def mag = file("${params.fixture_dir}/${meta.id}.metabat2_bins", checkIfExists: true)
    def tax = params.with_taxonomy ? [file("${params.fixture_dir}/${meta.id}.taxonomy.tsv", checkIfExists: true)] : []
    ch_input = Channel.of(tuple(meta, plasmid, [mag], tax))
    LINK_SEQUENCE(ch_input)
    LINK_SEQUENCE.out.links.view { meta, path -> "LINKS\t${meta.id}\t${path}" }
}
