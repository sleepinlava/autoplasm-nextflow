include { plasmidfinderResourceRecord } from '../lib/plasmidfinder_runtime'
include { resourceInput; taggedResourceInput } from '../lib/resource_inputs'
include { abricateResourceRecord } from '../lib/abricate_runtime'
include { integronfinderResourceRecord } from '../lib/integronfinder_runtime'
include { isescanResourceRecord } from '../lib/isescan_runtime'
include { reportEvidence; reportSamples } from '../lib/report_events'
include { selectedTools } from '../lib/tool_selection'

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
include { PLASMIDFINDER; PLASMIDFINDER_RESOURCE_PROBE } from '../modules/nf-core/plasmidfinder'
include { MOBSUITE_TYPER as MOB_TYPER } from '../modules/nf-core/mobsuite/typer'
include { COPLA } from '../modules/typing/copla'
include { MACSYFINDER_DOWNLOAD } from '../modules/nf-core/macsyfinder/download'
include { MACSYFINDER_SEARCH as CONJSCAN } from '../modules/nf-core/macsyfinder/search'
include { MACSYFINDER_SEARCH as MACSYFINDER } from '../modules/nf-core/macsyfinder/search'
include { BAKTA_BAKTA as BAKTA } from '../modules/nf-core/bakta/bakta'
include { AMRFINDERPLUS_RUN as AMRFINDERPLUS } from '../modules/nf-core/amrfinderplus/run'
include { ABRICATE_RUN as ABRICATE; ABRICATE_RESOURCE_PROBE } from '../modules/nf-core/abricate/run'
include { ISESCAN; ISESCAN_RESOURCE_PROBE } from '../modules/annotation/isescan'
include { INTEGRONFINDER; INTEGRONFINDER_RESOURCE_PROBE } from '../modules/nf-core/integronfinder'
include { PRODIGAL } from '../modules/nf-core/prodigal'
include { PROTEIN_INPUTS } from '../modules/annotation/protein_inputs'
include { MOBSUITE_RECON as MOB_SUITE_ANNOT } from '../modules/nf-core/mobsuite/recon'
include { RGI_MAIN as RGI } from '../modules/nf-core/rgi/main'
include { EGGNOGMAPPER as EGGNOG_MAPPER } from '../modules/nf-core/eggnogmapper'
include { MOBSUITE_RECON as MOB_RECON } from '../modules/nf-core/mobsuite/recon'
include { RECYCLER } from '../modules/binning/recycler'
include { RECYCLER_INPUTS } from '../modules/binning/recycler_inputs'

workflow PLASMID_DOWNSTREAM {
    take:
    ch_plasmids      // tuple(meta, plasmid_contigs.fasta) — non-empty only
    ch_graph         // legacy input; graph-node binning now runs beside assembly
    ch_contig_bam    // tuple(meta, bam) or empty
    ch_contig_table  // tuple(meta, coverm tsv) or empty
    ch_short_reads   // tuple(meta, r1, r2) or empty (Recycler graph-node alignment)
    ch_recycler_graph // tuple(meta, FASTG, graph_provenance.json) from same SPAdes task

    main:
    ch_report_events = Channel.empty()
    def run_conjscan    = selectedTools(params.typing_optional_tools).contains('conjscan')
    def run_macsyfinder = selectedTools(params.typing_optional_tools).contains('macsyfinder')
    def run_eggnog = selectedTools(params.annotation_optional_tools).contains('eggnog_mapper')
    def needs_proteins = run_conjscan || run_macsyfinder || run_eggnog
    ch_proteins = Channel.empty()
    if (needs_proteins || selectedTools(params.annotation_tools).contains('prodigal') || selectedTools(params.annotation_optional_tools).contains('prodigal')) {
        // One gene call supplies annotation and all protein consumers.
        PRODIGAL(ch_plasmids, Channel.value('gff'))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: PRODIGAL.out], '08_annotation', 'PRODIGAL'))
    }
    if (needs_proteins) {
        ch_gene_inputs = ch_plasmids
            .join(PRODIGAL.out.gene_annotations, failOnDuplicate: true, failOnMismatch: true)
            .join(PRODIGAL.out.amino_acid_fasta, failOnDuplicate: true, failOnMismatch: true)
            .join(PRODIGAL.out.nucleotide_fasta, failOnDuplicate: true, failOnMismatch: true)
        PROTEIN_INPUTS(ch_gene_inputs, Channel.value(file("${moduleDir}/../bin/prepare_prodigal_inputs.py", checkIfExists: true)))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: PROTEIN_INPUTS.out], '08_annotation', 'PROTEIN_INPUTS'))
        // Empty gene calls retain their manifest/state; protein tools do not
        // run on header-only input or report a biological negative for it.
        ch_proteins = PROTEIN_INPUTS.out.proteins.filter { meta, proteins, topology -> proteins.size() > 0 }
    }
    // ---------------- typing (06) ----------------
    if (selectedTools(params.typing_tools).contains('plasmidfinder')) {
        // nf-core module: bundled PlasmidFinder db (params.plasmidfinder_db no longer used)
        ch_plasmidfinder_helper = Channel.value(file("${moduleDir}/../bin/plasmidfinder_runtime_resources.py",checkIfExists:true))
        PLASMIDFINDER_RESOURCE_PROBE(ch_plasmids,ch_plasmidfinder_helper)
        ch_report_events = ch_report_events.mix(reportEvidence([channels: PLASMIDFINDER_RESOURCE_PROBE.out], '06_plasmid_typing', 'PLASMIDFINDER_RESOURCE_PROBE'))
        ch_plasmidfinder_identity = PLASMIDFINDER_RESOURCE_PROBE.out.identity.map { meta,receipt -> plasmidfinderResourceRecord(meta,receipt) }
        PLASMIDFINDER(ch_plasmids.join(ch_plasmidfinder_identity,failOnDuplicate:true,failOnMismatch:true),ch_plasmidfinder_helper)
        ch_report_events = ch_report_events.mix(reportEvidence([channels: PLASMIDFINDER.out], '06_plasmid_typing', 'PLASMIDFINDER'))
    }
    if (selectedTools(params.typing_tools).contains('mob_typer')) {
        // optional per-file db inputs (mash/meta/replicons/mask/mob/mpf/orit) left empty
        ch_mob_typer_preflight = Channel.value(file("${moduleDir}/../bin/mobsuite_preflight.py",checkIfExists:true))
        MOB_TYPER(ch_plasmids,
                  Channel.value(resourceInput(params.mob_suite_db)),
                  [], [], [], [], [], [], [],
                  false, false,ch_mob_typer_preflight)
        ch_report_events = ch_report_events.mix(reportEvidence([channels: MOB_TYPER.out], '06_plasmid_typing', 'MOB_TYPER'))
    }
    if (selectedTools(params.typing_optional_tools).contains('copla')) {
        def ResourceIdentity = new GroovyClassLoader().parseClass(new File("${moduleDir}/../lib/ResourceIdentity.groovy"))
        def resource = { location ->
            def directory = file(location, checkIfExists: true)
            tuple(directory, ResourceIdentity.capture(directory))
        }
        COPLA(ch_plasmids,
              Channel.value(file(params.copla_refgraph, checkIfExists: true)),
              Channel.value(file(params.copla_reflist, checkIfExists: true)),
              Channel.value(resource.call(params.copla_dir)),
              Channel.value(resource.call(params.copla_macsyfinder_dir)), Channel.value(file("${moduleDir}/../bin/run_copla_candidates.py", checkIfExists: true)))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: COPLA.out], '06_plasmid_typing', 'COPLA'))
    }
    if (run_conjscan || run_macsyfinder) {
        // Match the model release already declared in the project's test data.
        // Request once, only after at least one sample has actual proteins.
        MACSYFINDER_DOWNLOAD(ch_proteins.map { meta, proteins, topology -> 'CONJScan==2.1.0' }.first())
        ch_report_events = ch_report_events.mix(reportEvidence([channels: MACSYFINDER_DOWNLOAD.out], '06_plasmid_typing', 'MACSYFINDER_DOWNLOAD'))
    }
    if (run_conjscan) {
        CONJSCAN(ch_proteins, MACSYFINDER_DOWNLOAD.out.models.map { resourceInput(it) }, 'CONJScan/Plasmids all')
        ch_report_events = ch_report_events.mix(reportEvidence([channels: CONJSCAN.out], '06_plasmid_typing', 'CONJSCAN'))
    }
    if (run_macsyfinder) {
        MACSYFINDER(ch_proteins, MACSYFINDER_DOWNLOAD.out.models.map { resourceInput(it) }, 'CONJScan/Plasmids all')
        ch_report_events = ch_report_events.mix(reportEvidence([channels: MACSYFINDER.out], '06_plasmid_typing', 'MACSYFINDER'))
    }

    // ---------------- annotation (08) ----------------
    ch_bakta_dir = Channel.empty()
    if (selectedTools(params.annotation_tools).contains('bakta')) {
        // optional proteins/prodigal-tf/regions/hmms inputs left empty
        BAKTA(ch_plasmids,
              Channel.value(resourceInput(params.bakta_db)),
              [], [], [], [])
        ch_report_events = ch_report_events.mix(reportEvidence([channels: BAKTA.out], '08_annotation', 'BAKTA'))
        // clinker consumes the directory holding the *.gbff files (the task dir itself)
        ch_bakta_dir = BAKTA.out.gbff.map { meta, gbff -> tuple(meta, gbff.parent) }
    }
    if (selectedTools(params.annotation_tools).contains('amrfinderplus')) {
        AMRFINDERPLUS(ch_plasmids, Channel.value(resourceInput(params.amrfinderplus_db)))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: AMRFINDERPLUS.out], '08_annotation', 'AMRFINDERPLUS'))
    }
    if (selectedTools(params.annotation_tools).contains('abricate') || selectedTools(params.annotation_optional_tools).contains('abricate')) {
        // optional --datadir left empty; --db selected via ext.args
        ch_abricate_resource_helper = Channel.value(file("${moduleDir}/../bin/abricate_runtime_resources.pl", checkIfExists: true))
        ABRICATE_RESOURCE_PROBE(ch_plasmids, [], ch_abricate_resource_helper)
        ch_report_events = ch_report_events.mix(reportEvidence([channels: ABRICATE_RESOURCE_PROBE.out], '08_annotation', 'ABRICATE_RESOURCE_PROBE'))
        ch_abricate_identity = ABRICATE_RESOURCE_PROBE.out.identity.map { meta, receipt -> abricateResourceRecord(meta, receipt) }
        ABRICATE(ch_plasmids.join(ch_abricate_identity, failOnDuplicate: true, failOnMismatch: true), [], ch_abricate_resource_helper)
        ch_report_events = ch_report_events.mix(reportEvidence([channels: ABRICATE.out], '08_annotation', 'ABRICATE'))
    }
    if (selectedTools(params.annotation_tools).contains('isescan')) {
        ch_isescan_resource_helper = Channel.value(file("${moduleDir}/../bin/isescan_runtime_resources.py", checkIfExists: true))
        ISESCAN_RESOURCE_PROBE(ch_plasmids, ch_isescan_resource_helper)
        ch_report_events = ch_report_events.mix(reportEvidence([channels: ISESCAN_RESOURCE_PROBE.out], '08_annotation', 'ISESCAN_RESOURCE_PROBE'))
        ch_isescan_identity = ISESCAN_RESOURCE_PROBE.out.identity.map { meta, receipt -> isescanResourceRecord(meta, receipt) }
        ISESCAN(ch_plasmids.join(ch_isescan_identity, failOnDuplicate: true, failOnMismatch: true), ch_isescan_resource_helper)
        ch_report_events = ch_report_events.mix(reportEvidence([channels: ISESCAN.out], '08_annotation', 'ISESCAN'))
    }
    if (selectedTools(params.annotation_tools).contains('integronfinder')) {
        ch_integronfinder_resource_helper = Channel.value(file("${moduleDir}/../bin/integronfinder_runtime_resources.py",checkIfExists:true))
        ch_integronfinder_topology_helper = Channel.value(file("${moduleDir}/../bin/integronfinder_topology.py",checkIfExists:true))
        INTEGRONFINDER_RESOURCE_PROBE(ch_plasmids,ch_integronfinder_resource_helper,ch_integronfinder_topology_helper)
        ch_report_events = ch_report_events.mix(reportEvidence([channels: INTEGRONFINDER_RESOURCE_PROBE.out], '08_annotation', 'INTEGRONFINDER_RESOURCE_PROBE'))
        ch_integronfinder_identity = INTEGRONFINDER_RESOURCE_PROBE.out.identity.map { meta, receipt -> integronfinderResourceRecord(meta,receipt) }
        INTEGRONFINDER(ch_plasmids.join(ch_integronfinder_identity,failOnDuplicate:true,failOnMismatch:true),ch_integronfinder_resource_helper,ch_integronfinder_topology_helper)
        ch_report_events = ch_report_events.mix(reportEvidence([channels: INTEGRONFINDER.out], '08_annotation', 'INTEGRONFINDER'))
    }
    if (selectedTools(params.annotation_optional_tools).contains('mob_suite')) {
        // Uses the environment DB; native3.1.9 may auto-initialize/download if unprepared.
        // Resource preflight/native validation remain pending; do not launch unprepared.
        MOB_SUITE_ANNOT(ch_plasmids,Channel.value(file("${moduleDir}/../bin/mobsuite_preflight.py",checkIfExists:true)))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: MOB_SUITE_ANNOT.out], '08_annotation', 'MOB_SUITE_ANNOT'))
    }
    if (selectedTools(params.annotation_optional_tools).contains('rgi')) {
        // card = directory with card.json + card_database_v*.fasta; wildcard optional
        RGI(ch_plasmids,
            Channel.value(resourceInput(params.card_db)),
            Channel.value(resourceInput(null)), Channel.value(file("${moduleDir}/../bin/validate_rgi_card.py", checkIfExists: true)))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: RGI.out], '08_annotation', 'RGI'))
    }
    if (run_eggnog) {
        // search_mode=diamond with no explicit dmnd db (falls back to --data_dir)
        EGGNOG_MAPPER(ch_proteins.map { meta, proteins, topology -> tuple(meta, proteins) },
                      Channel.value(taggedResourceInput('diamond', null)),
                      Channel.value(resourceInput(params.eggnog_db)))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: EGGNOG_MAPPER.out], '08_annotation', 'EGGNOG_MAPPER'))
    }

    // ---------------- plasmid binning (05) ----------------
    if (selectedTools(params.plasmid_binning_tools).contains('mob_suite') || selectedTools(params.plasmid_binning_tools).contains('mob_recon')) {
        // Uses the environment DB; native3.1.9 may auto-initialize/download if unprepared.
        // Resource preflight/native validation remain pending; do not launch unprepared.
        MOB_RECON(ch_plasmids,Channel.value(file("${moduleDir}/../bin/mobsuite_preflight.py",checkIfExists:true)))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: MOB_RECON.out], '05_plasmid_binning', 'MOB_RECON'))
    }
    if (selectedTools(params.plasmid_binning_tools).contains('recycler')) {
        RECYCLER_INPUTS(ch_recycler_graph.join(ch_short_reads,
            failOnDuplicate: true, failOnMismatch: true))
        RECYCLER(RECYCLER_INPUTS.out.bam, Channel.value(tuple(file("${moduleDir}/../bin/validate_recycler_inputs.py", checkIfExists: true), file("${moduleDir}/../bin/run_recycler_checked.py", checkIfExists: true))))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: RECYCLER.out], '05_plasmid_binning', 'RECYCLER'))
    }

    emit:
    report_events = ch_report_events
    bakta_dir = ch_bakta_dir  // tuple(meta, dir containing *.gbff) for clinker; may be empty
}
