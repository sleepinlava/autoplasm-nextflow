/*
 * Shared per-sample downstream subworkflow over consensus plasmid contigs:
 * typing (06), annotation (08) and plasmid binning (05). All optional tools
 * are gated by params; disabled tools contribute empty channels and never
 * block the rest.
 */
include { PLASMIDFINDER } from '../modules/typing/plasmidfinder'
include { MOB_TYPER } from '../modules/typing/mob_typer'
include { COPLA } from '../modules/typing/copla'
include { CONJSCAN } from '../modules/typing/conjscan'
include { MACSYFINDER } from '../modules/typing/macsyfinder'
include { BAKTA } from '../modules/annotation/bakta'
include { AMRFINDERPLUS } from '../modules/annotation/amrfinderplus'
include { ABRICATE } from '../modules/annotation/abricate'
include { ISESCAN } from '../modules/annotation/isescan'
include { INTEGRONFINDER } from '../modules/annotation/integronfinder'
include { PRODIGAL } from '../modules/annotation/prodigal'
include { MOB_SUITE_ANNOT } from '../modules/annotation/mob_suite_annot'
include { RGI } from '../modules/annotation/rgi'
include { EGGNOG_MAPPER } from '../modules/annotation/eggnog'
include { PLASMAAG } from '../modules/binning/plasmaag'
include { GPLAS2 } from '../modules/binning/gplas2'
include { MOB_RECON } from '../modules/binning/mob_recon'
include { SCAPP_BIN } from '../modules/binning/scapp_bin'
include { RECYCLER } from '../modules/binning/recycler'

workflow PLASMID_DOWNSTREAM {
    take:
    ch_plasmids      // tuple(meta, plasmid_contigs.fasta) — non-empty only
    ch_graph         // tuple(meta, graph) or empty
    ch_contig_bam    // tuple(meta, bam) or empty
    ch_contig_table  // tuple(meta, coverm tsv) or empty
    ch_short_reads   // tuple(meta, r1, r2) or empty (SCAPP binning)

    main:
    // ---------------- typing (06) ----------------
    if (params.typing_tools.contains('plasmidfinder')) {
        PLASMIDFINDER(ch_plasmids, Channel.value(file(params.plasmidfinder_db, checkIfExists: true)))
    }
    if (params.typing_tools.contains('mob_typer')) {
        MOB_TYPER(ch_plasmids, Channel.value(file(params.mob_suite_db, checkIfExists: true)))
    }
    if (params.typing_optional_tools.contains('copla')) {
        COPLA(ch_plasmids,
              Channel.value(file(params.copla_refgraph, checkIfExists: true)),
              Channel.value(file(params.copla_reflist, checkIfExists: true)))
    }
    if (params.typing_optional_tools.contains('conjscan')) {
        CONJSCAN(ch_plasmids)
    }
    if (params.typing_optional_tools.contains('macsyfinder')) {
        MACSYFINDER(ch_plasmids)
    }

    // ---------------- annotation (08) ----------------
    ch_bakta_dir = Channel.empty()
    if (params.annotation_tools.contains('bakta')) {
        BAKTA(ch_plasmids, Channel.value(file(params.bakta_db, checkIfExists: true)))
        ch_bakta_dir = BAKTA.out.output_dir
    }
    if (params.annotation_tools.contains('amrfinderplus')) {
        AMRFINDERPLUS(ch_plasmids, Channel.value(file(params.amrfinderplus_db, checkIfExists: true)))
    }
    if (params.annotation_tools.contains('abricate')) {
        ABRICATE(ch_plasmids)
    }
    if (params.annotation_tools.contains('isescan')) {
        ISESCAN(ch_plasmids)
    }
    if (params.annotation_tools.contains('integronfinder')) {
        INTEGRONFINDER(ch_plasmids)
    }
    if (params.annotation_tools.contains('prodigal') || params.annotation_optional_tools.contains('prodigal')) {
        PRODIGAL(ch_plasmids)
    }
    if (params.annotation_optional_tools.contains('mob_suite')) {
        MOB_SUITE_ANNOT(ch_plasmids, Channel.value(file(params.mob_suite_db, checkIfExists: true)))
    }
    if (params.annotation_optional_tools.contains('rgi')) {
        RGI(ch_plasmids, Channel.value(file(params.card_db, checkIfExists: true)))
    }
    if (params.annotation_optional_tools.contains('eggnog_mapper')) {
        EGGNOG_MAPPER(ch_plasmids, Channel.value(file(params.eggnog_db, checkIfExists: true)))
    }

    // ---------------- plasmid binning (05) ----------------
    if (params.plasmid_binning_tools.contains('plasmaag')) {
        PLASMAAG(ch_plasmids.join(ch_contig_table))
    }
    if (params.plasmid_binning_tools.contains('gplas2')) {
        GPLAS2(ch_plasmids.join(ch_graph))
    }
    if (params.plasmid_binning_tools.contains('mob_suite') || params.plasmid_binning_tools.contains('mob_recon')) {
        MOB_RECON(ch_plasmids, Channel.value(file(params.mob_suite_db, checkIfExists: true)))
    }
    if (params.plasmid_binning_tools.contains('scapp')) {
        SCAPP_BIN(ch_graph.join(ch_short_reads))
    }
    if (params.plasmid_binning_tools.contains('recycler')) {
        RECYCLER(ch_graph.join(ch_plasmids).join(ch_contig_bam))
    }

    emit:
    bakta_dir = ch_bakta_dir  // tuple(meta, bakta_out) for clinker; may be empty
}
