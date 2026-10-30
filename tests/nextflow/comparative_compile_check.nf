nextflow.enable.dsl=2
include { BLAST_BLASTN } from '../../modules/nf-core/blast/blastn/main'
include { MUMMER } from '../../modules/comparative/mummer'
include { CLINKER } from '../../modules/comparative/clinker'
include { MMSEQS_EASYCLUSTER } from '../../modules/nf-core/mmseqs/easycluster/main'
include { PLASMID_CATALOG_PREPARE } from '../../modules/comparative/catalog_prepare'

workflow {
    // Parse/compile check only; processes are never invoked.
}
