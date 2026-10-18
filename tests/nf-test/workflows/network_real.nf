// P3 real-data chain: NETWORK_PREPARE + FASTSPAR on the real ENA contig
// abundance table (482 contigs x 6 samples; P4 product, see
// results/nf-test/ena-multi/cross/PROVENANCE.md). The P4 ENA run legitimately
// skips this branch (zero plasmid calls), so this wrapper exercises the two
// nodes with a real non-empty table.
// Backend: podman (autoplasm-r-analysis + fastspar images).
nextflow.enable.dsl = 2

include { NETWORK_PREPARE } from '../../../modules/cross_sample/network_prepare'
include { FASTSPAR } from '../../../modules/cross_sample/fastspar'

workflow {
    def table = file("${params.test_data}/cross/contig_abundance.tsv", checkIfExists: true)
    NETWORK_PREPARE(table)
    FASTSPAR(NETWORK_PREPARE.out.network_input)
}
