include { resourceInput; taggedResourceInput } from '../lib/resource_inputs'
include { semibinResourceRecord } from '../lib/semibin_runtime'
include { reportEvidence; reportSamples } from '../lib/report_events'
include { selectedTools } from '../lib/tool_selection'
include { magSelectionError } from '../lib/mag_selection'

/*
 * MAG host-genome subworkflow (mag_host_genomes): MetaBAT2 /
 * CONCOCT / SemiBin binners, optional DAS Tool aggregation, CheckM2 quality,
 * GTDB-Tk taxonomy. All optional via params.mag_tools.
 *
 * Binner steps run the nf-core modules. The official bam-consuming
 * contracts (METABAT2_JGISUMMARIZEBAMCONTIGDEPTHS,
 * CONCOCT_CONCOCTCOVERAGETABLE) require a BAI next to the BAM, so the
 * local SAMTOOLS_INDEX bridge indexes the incoming bam first. The nf-core
 * CONCOCT chain derives coverage from bam, so the coverm table input is
 * kept in the signature but no longer consumed.
 */
include { SAMTOOLS_INDEX } from '../modules/mag/samtools_index'
include { METABAT2_JGISUMMARIZEBAMCONTIGDEPTHS } from '../modules/nf-core/metabat2/jgisummarizebamcontigdepths/main'
include { METABAT2_METABAT2 as METABAT2 } from '../modules/nf-core/metabat2/metabat2/main'
include { CONCOCT_CUTUPFASTA } from '../modules/nf-core/concoct/cutupfasta/main'
include { CONCOCT_CONCOCTCOVERAGETABLE } from '../modules/nf-core/concoct/concoctcoveragetable/main'
include { CONCOCT_CONCOCT } from '../modules/nf-core/concoct/concoct/main'
include { CONCOCT_MERGECUTUPCLUSTERING } from '../modules/nf-core/concoct/mergecutupclustering/main'
include { CONCOCT_EXTRACTFASTABINS as CONCOCT } from '../modules/nf-core/concoct/extractfastabins/main'
include { SEMIBIN_SINGLEEASYBIN as SEMIBIN; SEMIBIN_RESOURCE_PROBE } from '../modules/nf-core/semibin/singleeasybin/main'
include { DASTOOL_FASTATOCONTIG2BIN as SCAFFOLDS2BIN_METABAT2 } from '../modules/nf-core/dastool/fastatocontig2bin/main'
include { DASTOOL_FASTATOCONTIG2BIN as SCAFFOLDS2BIN_CONCOCT } from '../modules/nf-core/dastool/fastatocontig2bin/main'
include { DASTOOL_FASTATOCONTIG2BIN as SCAFFOLDS2BIN_SEMIBIN } from '../modules/nf-core/dastool/fastatocontig2bin/main'
include { DASTOOL_DASTOOL as DAS_TOOL } from '../modules/nf-core/dastool/dastool/main'
include { CHECKM2_PREDICT as CHECKM2 } from '../modules/nf-core/checkm2/predict/main'
include { GTDBTK_CLASSIFYWF as GTDBTK } from '../modules/nf-core/gtdbtk/classifywf/main'

workflow MAG_HOST {
    take:
    ch_assembly     // tuple(meta, fasta)
    ch_contig_bam   // tuple(meta, bam)
    ch_contig_table // tuple(meta, coverm tsv); unused by the nf-core CONCOCT chain

    main:
    ch_report_events = Channel.empty()
    def magError = magSelectionError(params.mag_tools)
    if (magError) error(magError)
    // Only index when a MAG tool actually consumes the BAM; the bridge is
    // pointless (and fails container-less hosts) when mag_tools is empty.
    ch_bam_bai = Channel.empty()
    if (selectedTools(params.mag_tools).any { it in ['metabat2', 'concoct'] }) {
        ch_bam_bai = ch_contig_bam
            .join(SAMTOOLS_INDEX(ch_contig_bam).bai, failOnDuplicate: true, failOnMismatch: true)
            ch_report_events = ch_report_events.mix(reportEvidence([channels: SAMTOOLS_INDEX.out], '07_host_prediction', 'SAMTOOLS_INDEX'))
    }

    ch_metabat2_bins = Channel.empty()
    if (selectedTools(params.mag_tools).contains('metabat2')) {
        METABAT2_JGISUMMARIZEBAMCONTIGDEPTHS(ch_bam_bai)
        ch_report_events = ch_report_events.mix(reportEvidence([channels: METABAT2_JGISUMMARIZEBAMCONTIGDEPTHS.out], '07_host_prediction', 'METABAT2_JGISUMMARIZEBAMCONTIGDEPTHS'))
        METABAT2(ch_assembly.join(METABAT2_JGISUMMARIZEBAMCONTIGDEPTHS.out.depth,
                                 failOnDuplicate: true, failOnMismatch: true))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: METABAT2.out], '07_host_prediction', 'METABAT2'))
        ch_metabat2_bins = METABAT2.out.fasta
    }

    ch_concoct_bins = Channel.empty()
    if (selectedTools(params.mag_tools).contains('concoct')) {
        CONCOCT_CUTUPFASTA(ch_assembly, Channel.value(true), Channel.value(file("${moduleDir}/../bin/run_concoct_cut_checked.py", checkIfExists: true)))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: CONCOCT_CUTUPFASTA.out], '07_host_prediction', 'CONCOCT_CUTUPFASTA'))
        CONCOCT_CONCOCTCOVERAGETABLE(
            CONCOCT_CUTUPFASTA.out.bed.join(ch_bam_bai, failOnDuplicate: true, failOnMismatch: true)
        )
        ch_report_events = ch_report_events.mix(reportEvidence([channels: CONCOCT_CONCOCTCOVERAGETABLE.out], '07_host_prediction', 'CONCOCT_CONCOCTCOVERAGETABLE'))
        CONCOCT_CONCOCT(
            CONCOCT_CONCOCTCOVERAGETABLE.out.tsv.join(CONCOCT_CUTUPFASTA.out.fasta,
                                                   failOnDuplicate: true, failOnMismatch: true)
        )
        ch_report_events = ch_report_events.mix(reportEvidence([channels: CONCOCT_CONCOCT.out], '07_host_prediction', 'CONCOCT_CONCOCT'))
        CONCOCT_MERGECUTUPCLUSTERING(CONCOCT_CONCOCT.out.clustering_csv)
        ch_report_events = ch_report_events.mix(reportEvidence([channels: CONCOCT_MERGECUTUPCLUSTERING.out], '07_host_prediction', 'CONCOCT_MERGECUTUPCLUSTERING'))
        CONCOCT(ch_assembly.join(CONCOCT_MERGECUTUPCLUSTERING.out.csv,
                                failOnDuplicate: true, failOnMismatch: true))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: CONCOCT.out], '07_host_prediction', 'CONCOCT'))
        ch_concoct_bins = CONCOCT.out.fasta
    }

    ch_semibin_bins = Channel.empty()
    if (selectedTools(params.mag_tools).contains('semibin')) {
        ch_semibin_input = ch_assembly.join(ch_contig_bam, failOnDuplicate: true, failOnMismatch: true)
        ch_semibin_resource_helper = Channel.value(file("${moduleDir}/../bin/semibin_runtime_resources.py", checkIfExists: true))
        SEMIBIN_RESOURCE_PROBE(ch_semibin_input, ch_semibin_resource_helper)
        ch_semibin_identity = SEMIBIN_RESOURCE_PROBE.out.identity.map { meta, receipt -> semibinResourceRecord(meta, receipt) }
        SEMIBIN(ch_semibin_input.join(ch_semibin_identity, failOnDuplicate: true, failOnMismatch: true),
                Channel.value(file("${moduleDir}/../bin/semibin_output_state.py", checkIfExists: true)),
                ch_semibin_resource_helper)
        ch_report_events = ch_report_events.mix(reportEvidence([channels: SEMIBIN.out], '07_host_prediction', 'SEMIBIN'))
        ch_semibin_bins = SEMIBIN.out.output_fasta
    }

    // Without DAS Tool the entry guard permits exactly one selected binner.
    ch_final_bins = ch_metabat2_bins.mix(ch_concoct_bins, ch_semibin_bins)
    if (selectedTools(params.mag_tools).contains('das_tool')) {
        ch_s2b_metabat2 = SCAFFOLDS2BIN_METABAT2(ch_metabat2_bins, Channel.value('fa')).fastatocontig2bin
        ch_report_events = ch_report_events.mix(reportEvidence([channels: SCAFFOLDS2BIN_METABAT2.out], '07_host_prediction', 'SCAFFOLDS2BIN_METABAT2'))
        ch_s2b_concoct = SCAFFOLDS2BIN_CONCOCT(ch_concoct_bins, Channel.value('fa')).fastatocontig2bin
        ch_report_events = ch_report_events.mix(reportEvidence([channels: SCAFFOLDS2BIN_CONCOCT.out], '07_host_prediction', 'SCAFFOLDS2BIN_CONCOCT'))
        ch_s2b_semibin = SCAFFOLDS2BIN_SEMIBIN(ch_semibin_bins, Channel.value('fa')).fastatocontig2bin
        ch_report_events = ch_report_events.mix(reportEvidence([channels: SCAFFOLDS2BIN_SEMIBIN.out], '07_host_prediction', 'SCAFFOLDS2BIN_SEMIBIN'))
        ch_das_in = ch_assembly
            // Group all available predictions by sample. A binner returning no
            // bins must not discard another binner's nonempty predictions.
            .join(ch_s2b_metabat2.mix(ch_s2b_concoct, ch_s2b_semibin).groupTuple(),
                  remainder: true, failOnDuplicate: true)
            .filter { meta, assembly, tsvs ->
                if (!assembly) error("MAG predictions have no assembly for ${meta.id}")
                tsvs != null
            }
            .map { meta, assembly, tsvs -> tuple(meta, assembly, tsvs, []) }
        DAS_TOOL(ch_das_in, Channel.value(resourceInput(null)))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: DAS_TOOL.out], '07_host_prediction', 'DAS_TOOL'))
        ch_final_bins = DAS_TOOL.out.bins
    }

    if (selectedTools(params.mag_tools).contains('checkm2')) {
        CHECKM2(
            ch_final_bins,
            Channel.value(taggedResourceInput([id: 'checkm2_db'], params.checkm2_db))
        )
        ch_report_events = ch_report_events.mix(reportEvidence([channels: CHECKM2.out], '07_host_prediction', 'CHECKM2'))
    }

    ch_taxonomy = Channel.empty()
    if (selectedTools(params.mag_tools).contains('gtdbtk')) {
        GTDBTK(
            ch_final_bins,
            Channel.value(taggedResourceInput([id: 'gtdbtk_db'], params.gtdbtk_db)),
            false
        , Channel.value(file("${moduleDir}/../bin/normalize_gtdb_bins.py", checkIfExists: true)))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: GTDBTK.out], '07_host_prediction', 'GTDBTK'))
        ch_taxonomy = GTDBTK.out.summary
    }

    emit:
    report_events = ch_report_events
    mag_bins = ch_final_bins  // tuple(meta, bin fasta/list); samples with no bins are absent
    taxonomy = ch_taxonomy    // tuple(meta, [gtdbtk summary tsv, ...]); may be empty
}
