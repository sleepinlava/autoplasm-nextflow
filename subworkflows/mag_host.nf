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
include { SEMIBIN_SINGLEEASYBIN as SEMIBIN } from '../modules/nf-core/semibin/singleeasybin/main'
include { DASTOOL_FASTATOCONTIG2BIN as SCAFFOLDS2BIN_METABAT2 } from '../modules/nf-core/dastool/fastatocontig2bin/main'
include { DASTOOL_FASTATOCONTIG2BIN as SCAFFOLDS2BIN_CONCOCT } from '../modules/nf-core/dastool/fastatocontig2bin/main'
include { DASTOOL_DASTOOL as DAS_TOOL } from '../modules/nf-core/dastool/dastool/main'
include { CHECKM2_PREDICT as CHECKM2 } from '../modules/nf-core/checkm2/predict/main'
include { GTDBTK_CLASSIFYWF as GTDBTK } from '../modules/nf-core/gtdbtk/classifywf/main'

workflow MAG_HOST {
    take:
    ch_assembly     // tuple(meta, fasta)
    ch_contig_bam   // tuple(meta, bam)
    ch_contig_table // tuple(meta, coverm tsv); unused by the nf-core CONCOCT chain

    main:
    // Only index when a MAG tool actually consumes the BAM; the bridge is
    // pointless (and fails container-less hosts) when mag_tools is empty.
    ch_bam_bai = Channel.empty()
    if (params.mag_tools) {
        ch_bam_bai = ch_contig_bam
            .join(SAMTOOLS_INDEX(ch_contig_bam).bai)
    }

    ch_metabat2_bins = Channel.empty()
    if (params.mag_tools.contains('metabat2')) {
        METABAT2_JGISUMMARIZEBAMCONTIGDEPTHS(ch_bam_bai)
        METABAT2(ch_assembly.join(METABAT2_JGISUMMARIZEBAMCONTIGDEPTHS.out.depth))
        ch_metabat2_bins = METABAT2.out.fasta
    }

    ch_concoct_bins = Channel.empty()
    if (params.mag_tools.contains('concoct')) {
        CONCOCT_CUTUPFASTA(ch_assembly, Channel.value(true))
        CONCOCT_CONCOCTCOVERAGETABLE(
            CONCOCT_CUTUPFASTA.out.bed.join(ch_bam_bai)
        )
        CONCOCT_CONCOCT(
            CONCOCT_CONCOCTCOVERAGETABLE.out.tsv.join(CONCOCT_CUTUPFASTA.out.fasta)
        )
        CONCOCT_MERGECUTUPCLUSTERING(CONCOCT_CONCOCT.out.clustering_csv)
        CONCOCT(ch_assembly.join(CONCOCT_MERGECUTUPCLUSTERING.out.csv))
        ch_concoct_bins = CONCOCT.out.fasta
    }

    if (params.mag_tools.contains('semibin')) {
        SEMIBIN(ch_assembly.join(ch_contig_bam))
    }

    ch_final_bins = ch_metabat2_bins
    if (params.mag_tools.contains('das_tool')) {
        ch_s2b_metabat2 = SCAFFOLDS2BIN_METABAT2(ch_metabat2_bins, Channel.value('fa')).fastatocontig2bin
        ch_s2b_concoct = SCAFFOLDS2BIN_CONCOCT(ch_concoct_bins, Channel.value('fa')).fastatocontig2bin
        ch_das_in = ch_assembly
            .join(ch_s2b_metabat2.mix(ch_s2b_concoct).groupTuple())
            .map { meta, assembly, tsvs -> tuple(meta, assembly, tsvs, []) }
        DAS_TOOL(ch_das_in, [])
        ch_final_bins = DAS_TOOL.out.bins
    }

    if (params.mag_tools.contains('checkm2')) {
        CHECKM2(
            ch_final_bins,
            Channel.value([[id: 'checkm2_db'], file(params.checkm2_db, checkIfExists: true)])
        )
    }

    ch_taxonomy = Channel.empty()
    if (params.mag_tools.contains('gtdbtk')) {
        GTDBTK(
            ch_final_bins,
            Channel.value([[id: 'gtdbtk_db'], file(params.gtdbtk_db, checkIfExists: true)]),
            false
        )
        ch_taxonomy = GTDBTK.out.summary
    }

    emit:
    mag_bins = ch_final_bins  // tuple(meta, [bin fasta, ...]); may be empty
    taxonomy = ch_taxonomy    // tuple(meta, [gtdbtk summary tsv, ...]); may be empty
}
