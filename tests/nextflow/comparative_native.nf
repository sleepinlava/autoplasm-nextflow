nextflow.enable.dsl=2
include { MMSEQS_EASYCLUSTER } from '../../modules/nf-core/mmseqs/easycluster/main'
include { PRODIGAL } from '../../modules/nf-core/prodigal/main'
include { PLASMID_CATALOG_PREPARE } from '../../modules/comparative/catalog_prepare'

workflow {
    mmseqs_in = Channel.fromList(params.sequences).map { row -> tuple([id: row.id], file(row.fasta, checkIfExists: true)) }
    MMSEQS_EASYCLUSTER(mmseqs_in)
    PRODIGAL(Channel.of(tuple([id: 'pUTI89'], file(params.prodigal_genome, checkIfExists: true))), Channel.value('gff'))
    PLASMID_CATALOG_PREPARE(Channel.fromList(params.sequences).map { row -> file(row.fasta, checkIfExists: true) }.collect(),
        file("${projectDir}/../../bin/plasmid_catalog_prepare.R", checkIfExists:true))
}
