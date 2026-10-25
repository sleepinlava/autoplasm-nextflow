// P3 network chain. test_data/cross/contig_abundance.tsv must contain
// measured integer raw_count on a shared reference. Historical coverage-only
// ENA tables must be regenerated; they are not valid count input. The caller
// selects the minimum eligible cohort explicitly for smaller fixtures.
nextflow.enable.dsl = 2

include { NETWORK_PREPARE } from '../../../modules/cross_sample/network_prepare'
include { FASTSPAR } from '../../../modules/cross_sample/fastspar'

workflow {
    def table = file("${params.test_data}/cross/contig_abundance.tsv", checkIfExists: true)
    NETWORK_PREPARE(table, [], [file("${moduleDir}/../../../bin/network_prepare.R",checkIfExists:true), file("${moduleDir}/../../../bin/statistics_input_contract.R",checkIfExists:true)])
    FASTSPAR(NETWORK_PREPARE.out.eligible_input)
}
