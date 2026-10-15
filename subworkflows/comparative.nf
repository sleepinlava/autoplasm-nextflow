/*
 * Comparative genomics subworkflow (DAG category comparative_genomics, 09):
 * catalog preparation (internal handler) + MMseqs2 cross-sample clustering
 * (default), plus optional per-sample BLASTn / MUMmer / clinker.
 *
 * The catalog step globs the published 04_plasmid_detection directory, like
 * the ABI handler does (avoids staging name collisions of per-sample
 * plasmid_contigs.fasta files).
 */
include { PLASMID_CATALOG_PREPARE } from '../modules/comparative/catalog_prepare'
include { MMSEQS2 } from '../modules/comparative/mmseqs2'
include { BLASTN } from '../modules/comparative/blast'
include { MUMMER } from '../modules/comparative/mummer'
include { CLINKER } from '../modules/comparative/clinker'

workflow COMPARATIVE {
    take:
    ch_plasmids  // tuple(meta, fasta)
    ch_bakta_dir // tuple(meta, bakta out dir); may be empty

    main:
    ch_catalog = Channel.empty()
    if (params.comparative_tools.contains('mmseqs2')) {
        PLASMID_CATALOG_PREPARE(ch_plasmids.map { meta, f -> meta.id }.collect())
        MMSEQS2(PLASMID_CATALOG_PREPARE.out.combined)
    }
    if (params.comparative_optional_tools.contains('blast')) {
        BLASTN(ch_plasmids, Channel.value(file(params.blast_db, checkIfExists: true)))
    }
    if (params.comparative_optional_tools.contains('mummer')) {
        MUMMER(ch_plasmids, Channel.value(file(params.reference_plasmids, checkIfExists: true)))
    }
    if (params.comparative_optional_tools.contains('clinker')) {
        CLINKER(ch_bakta_dir)
    }
}
