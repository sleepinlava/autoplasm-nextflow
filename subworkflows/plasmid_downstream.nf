/*
 * Shared per-sample downstream subworkflow over consensus plasmid contigs:
 * typing (06), annotation (08) and plasmid binning (05). All optional tools
 * are gated by params; disabled tools contribute empty channels and never
 * block the rest.
 *
 * Tool implementations are the vendored nf-core modules (modules/nf-core);
 * process names are kept stable through aliases so that reporting, trace
 * validation and publish layout stay unchanged. Per-tool CLI flags and
 * publishDir replication for the nf-core modules live in
 * conf/nfcore_downstream.config.
 */
include { PLASMIDFINDER } from '../modules/nf-core/plasmidfinder'
include { MOBSUITE_TYPER as MOB_TYPER } from '../modules/nf-core/mobsuite/typer'
include { COPLA } from '../modules/typing/copla'
include { MACSYFINDER_DOWNLOAD } from '../modules/nf-core/macsyfinder/download'
include { MACSYFINDER_SEARCH as CONJSCAN } from '../modules/nf-core/macsyfinder/search'
include { MACSYFINDER_SEARCH as MACSYFINDER } from '../modules/nf-core/macsyfinder/search'
include { BAKTA_BAKTA as BAKTA } from '../modules/nf-core/bakta/bakta'
include { AMRFINDERPLUS_RUN as AMRFINDERPLUS } from '../modules/nf-core/amrfinderplus/run'
include { ABRICATE_RUN as ABRICATE } from '../modules/nf-core/abricate/run'
include { ISESCAN } from '../modules/annotation/isescan'
include { INTEGRONFINDER } from '../modules/nf-core/integronfinder'
include { PRODIGAL } from '../modules/nf-core/prodigal'
include { MOBSUITE_RECON as MOB_SUITE_ANNOT } from '../modules/nf-core/mobsuite/recon'
include { RGI_MAIN as RGI } from '../modules/nf-core/rgi/main'
include { EGGNOGMAPPER as EGGNOG_MAPPER } from '../modules/nf-core/eggnogmapper'
include { PLASMAAG } from '../modules/binning/plasmaag'
include { GPLAS2 } from '../modules/binning/gplas2'
include { MOBSUITE_RECON as MOB_RECON } from '../modules/nf-core/mobsuite/recon'
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
        // nf-core module: bundled PlasmidFinder db (params.plasmidfinder_db no longer used)
        PLASMIDFINDER(ch_plasmids)
    }
    if (params.typing_tools.contains('mob_typer')) {
        // optional per-file db inputs (mash/meta/replicons/mask/mob/mpf/orit) left empty
        MOB_TYPER(ch_plasmids,
                  Channel.value(file(params.mob_suite_db, checkIfExists: true)),
                  [], [], [], [], [], [], [],
                  false, false)
    }
    if (params.typing_optional_tools.contains('copla')) {
        COPLA(ch_plasmids,
              Channel.value(file(params.copla_refgraph, checkIfExists: true)),
              Channel.value(file(params.copla_reflist, checkIfExists: true)))
    }
    def run_conjscan    = params.typing_optional_tools.contains('conjscan')
    def run_macsyfinder = params.typing_optional_tools.contains('macsyfinder')
    if (run_conjscan || run_macsyfinder) {
        // CONJScan models via macsydata (macsyfinder >= 2.1.2 no longer ships them)
        MACSYFINDER_DOWNLOAD(Channel.value('CONJ'))
    }
    if (run_conjscan) {
        CONJSCAN(ch_plasmids, MACSYFINDER_DOWNLOAD.out.models, 'CONJ')
    }
    if (run_macsyfinder) {
        MACSYFINDER(ch_plasmids, MACSYFINDER_DOWNLOAD.out.models, 'CONJ')
    }

    // ---------------- annotation (08) ----------------
    ch_bakta_dir = Channel.empty()
    if (params.annotation_tools.contains('bakta')) {
        // optional proteins/prodigal-tf/regions/hmms inputs left empty
        BAKTA(ch_plasmids,
              Channel.value(file(params.bakta_db, checkIfExists: true)),
              [], [], [], [])
        // clinker consumes the directory holding the *.gbff files (the task dir itself)
        ch_bakta_dir = BAKTA.out.gbff.map { meta, gbff -> tuple(meta, gbff.parent) }
    }
    if (params.annotation_tools.contains('amrfinderplus')) {
        AMRFINDERPLUS(ch_plasmids, Channel.value(file(params.amrfinderplus_db, checkIfExists: true)))
    }
    if (params.annotation_tools.contains('abricate')) {
        // optional --datadir left empty; --db selected via ext.args
        ABRICATE(ch_plasmids, [])
    }
    if (params.annotation_tools.contains('isescan')) {
        ISESCAN(ch_plasmids)
    }
    if (params.annotation_tools.contains('integronfinder')) {
        INTEGRONFINDER(ch_plasmids)
    }
    if (params.annotation_tools.contains('prodigal') || params.annotation_optional_tools.contains('prodigal')) {
        PRODIGAL(ch_plasmids, Channel.value('gff'))
    }
    if (params.annotation_optional_tools.contains('mob_suite')) {
        // nf-core module: no db input (uses mob_suite 3.1.9 bundled db)
        MOB_SUITE_ANNOT(ch_plasmids)
    }
    if (params.annotation_optional_tools.contains('rgi')) {
        // card = directory with card.json + card_database_v*.fasta; wildcard optional
        RGI(ch_plasmids,
            Channel.value(file(params.card_db, checkIfExists: true)),
            [])
    }
    if (params.annotation_optional_tools.contains('eggnog_mapper')) {
        // search_mode=diamond with no explicit dmnd db (falls back to --data_dir)
        EGGNOG_MAPPER(ch_plasmids,
                      Channel.value(['diamond', []]),
                      Channel.value(file(params.eggnog_db, checkIfExists: true)))
    }

    // ---------------- plasmid binning (05) ----------------
    if (params.plasmid_binning_tools.contains('plasmaag')) {
        PLASMAAG(ch_plasmids.join(ch_contig_table))
    }
    if (params.plasmid_binning_tools.contains('gplas2')) {
        GPLAS2(ch_plasmids.join(ch_graph))
    }
    if (params.plasmid_binning_tools.contains('mob_suite') || params.plasmid_binning_tools.contains('mob_recon')) {
        // nf-core module: no db input (uses mob_suite 3.1.9 bundled db)
        MOB_RECON(ch_plasmids)
    }
    if (params.plasmid_binning_tools.contains('scapp')) {
        SCAPP_BIN(ch_graph.join(ch_short_reads))
    }
    if (params.plasmid_binning_tools.contains('recycler')) {
        RECYCLER(ch_graph.join(ch_contig_bam))
    }

    emit:
    bakta_dir = ch_bakta_dir  // tuple(meta, dir containing *.gbff) for clinker; may be empty
}
