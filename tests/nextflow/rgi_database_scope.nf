nextflow.enable.dsl=2

include { RGI_MAIN as RGI } from '../../modules/nf-core/rgi/main/main'

workflow {
    reads = Channel.fromList(params.records).map { row -> tuple([id: row.id], file(row.fasta, checkIfExists: true)) }
    RGI(reads, Channel.value(file(params.card, checkIfExists: true)), [], Channel.value(file("${moduleDir}/../../bin/validate_rgi_card.py", checkIfExists: true)))
    RGI.out.db_version.view { "DB_VERSION_CAPTURE=${it}" }
}
