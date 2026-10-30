include { resourceInput; taggedResourceInput } from '../lib/resource_inputs'
include { reportEvidence; reportSamples } from '../lib/report_events'
include { selectedTools } from '../lib/tool_selection'

/*
 * Comparative genomics subworkflow (stage 09 comparative_genomics):
 * catalog preparation (bin/plasmid_catalog_prepare.R) + MMseqs2 cross-sample
 * clustering (default), plus optional per-sample BLASTn / MUMmer / clinker.
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
    ch_report_events = Channel.empty()
    if (selectedTools(params.comparative_tools).contains('mmseqs2')) {
        ch_catalog_files = ch_plasmids
            .map { meta, fasta -> fasta }
            .collect()
            .filter { files -> !files.isEmpty() }
        PLASMID_CATALOG_PREPARE(ch_catalog_files,
            file("${moduleDir}/../bin/plasmid_catalog_prepare.R", checkIfExists:true))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: PLASMID_CATALOG_PREPARE.out], '09_comparative_genomics', 'PLASMID_CATALOG_PREPARE'))
        // The nf-core module takes a meta-tagged sequence channel; the meta id
        // doubles as the easy-cluster output prefix, so published file names
        // stay plasmid_catalog_cluster.tsv / plasmid_catalog_rep_seq.fasta.
        ch_catalog_domain = PLASMID_CATALOG_PREPARE.out.samples
            .splitCsv(header:true, sep:'\t').map { row -> row.sample_id }.toList()
            .map { ids -> [samples: ids] }
        MMSEQS2(PLASMID_CATALOG_PREPARE.out.combined.combine(ch_catalog_domain).map { fasta, domain ->
            tuple([id:'plasmid_catalog', cohort:true, cohort_samples:domain.samples], fasta)
        })
        ch_report_events = ch_report_events.mix(reportEvidence([channels: MMSEQS2.out], '09_comparative_genomics', 'MMSEQS2'))
    }
    if (selectedTools(params.comparative_optional_tools).contains('blast')) {
        BLASTN(
            ch_plasmids,
            Channel.value(taggedResourceInput([id: 'blast_db'], params.blast_db)),
            [],     // taxidlist
            [],     // taxids
            false   // negative_tax
        )
        ch_report_events = ch_report_events.mix(reportEvidence([channels: BLASTN.out], '09_comparative_genomics', 'BLASTN'))
    }
    if (selectedTools(params.comparative_optional_tools).contains('mummer')) {
        MUMMER(ch_plasmids, Channel.value(file(params.reference_plasmids, checkIfExists: true)))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: MUMMER.out], '09_comparative_genomics', 'MUMMER'))
    }
    if (selectedTools(params.comparative_optional_tools).contains('clinker')) {
        CLINKER(ch_bakta_dir)
        ch_report_events = ch_report_events.mix(reportEvidence([channels: CLINKER.out], '09_comparative_genomics', 'CLINKER'))
    }
    emit:
    report_events = ch_report_events
}
