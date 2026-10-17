/*
 * Comparative genomics subworkflow (DAG category comparative_genomics, 09):
 * catalog preparation (internal handler) + MMseqs2 cross-sample clustering
 * (default), plus optional per-sample BLASTn / MUMmer / clinker.
 *
 * The catalog step receives the consensus FASTA files through their channel,
 * so task dependencies do not rely on asynchronous publication.
 *
 * MMSEQS2 / BLASTN are the vendored nf-core modules (mmseqs/easycluster,
 * blast/blastn) included under their original process names; publishDir and
 * tool arguments for them live in conf/nfcore_host_comparative.config.
 */
include { PLASMID_CATALOG_PREPARE } from '../modules/comparative/catalog_prepare'
include { MMSEQS_EASYCLUSTER as MMSEQS2 } from '../modules/nf-core/mmseqs/easycluster'
include { BLAST_BLASTN as BLASTN } from '../modules/nf-core/blast/blastn'
include { MUMMER } from '../modules/comparative/mummer'
include { CLINKER } from '../modules/comparative/clinker'

workflow COMPARATIVE {
    take:
    ch_plasmids  // tuple(meta, fasta)
    ch_bakta_dir // tuple(meta, bakta out dir); may be empty

    main:
    if (params.comparative_tools.contains('mmseqs2')) {
        ch_catalog_files = ch_plasmids
            .map { meta, fasta -> fasta }
            .collect()
            .filter { files -> !files.isEmpty() }
        PLASMID_CATALOG_PREPARE(ch_catalog_files)
        // The nf-core module takes a meta-tagged sequence channel; the meta id
        // doubles as the easy-cluster output prefix, so published file names
        // stay plasmid_catalog_cluster.tsv / plasmid_catalog_rep_seq.fasta.
        MMSEQS2(PLASMID_CATALOG_PREPARE.out.combined.map { fasta -> tuple([id: 'plasmid_catalog'], fasta) })
    }
    if (params.comparative_optional_tools.contains('blast')) {
        BLASTN(
            ch_plasmids,
            Channel.value(tuple([id: 'blast_db'], file(params.blast_db, checkIfExists: true))),
            [],     // taxidlist
            [],     // taxids
            false   // negative_tax
        )
    }
    if (params.comparative_optional_tools.contains('mummer')) {
        MUMMER(ch_plasmids, Channel.value(file(params.reference_plasmids, checkIfExists: true)))
    }
    if (params.comparative_optional_tools.contains('clinker')) {
        CLINKER(ch_bakta_dir)
    }
}
