/*
 * Plasmid abundance subworkflow (DAG category abundance, 10): map reads to
 * the consensus plasmid contigs and estimate coverage with CoverM. Hybrid
 * samples run a short-read chain and a long-read chain in parallel
 * (abundance_*_short / abundance_*_long in the DAG).
 */
include { BOWTIE2_ABUNDANCE } from '../modules/abundance/bowtie2_abundance'
include { MINIMAP2_ABUNDANCE } from '../modules/abundance/minimap2_abundance'
include { SAMTOOLS_SORT_ABUND; SAMTOOLS_SORT_ABUND as SAMTOOLS_SORT_ABUND_LONG } from '../modules/abundance/samtools_abundance'
include { COVERM_ABUNDANCE; COVERM_ABUNDANCE as COVERM_ABUNDANCE_LONG } from '../modules/abundance/coverm_abundance'

workflow PLASMID_ABUNDANCE {
    take:
    ch_plasmids    // tuple(meta, plasmid_contigs.fasta)
    ch_short_reads // tuple(meta, r1, r2); empty when no short reads
    ch_long_reads  // tuple(meta, fastq); empty when no long reads
    long_preset    // val: minimap2 preset
    hybrid         // val: boolean — emit short/long labelled outputs

    main:
    def short_lbl  = hybrid ? '.short' : ''
    def long_lbl   = hybrid ? '.long' : ''

    ch_short_sam = BOWTIE2_ABUNDANCE(
        ch_plasmids.join(ch_short_reads)
            .map { meta, contigs, r1, r2 -> tuple(meta, contigs, r1, r2, short_lbl) }
    ).alignment
    ch_long_sam = MINIMAP2_ABUNDANCE(
        ch_plasmids.join(ch_long_reads)
            .map { meta, contigs, lr -> tuple(meta, contigs, lr, long_lbl) },
        long_preset
    ).alignment

    ch_short_bam = SAMTOOLS_SORT_ABUND(ch_short_sam).bam
    ch_long_bam = SAMTOOLS_SORT_ABUND_LONG(ch_long_sam).bam

    ch_short_abund = COVERM_ABUNDANCE(ch_short_bam).abundance
    ch_long_abund = COVERM_ABUNDANCE_LONG(ch_long_bam).abundance

    emit:
    short_abundance = ch_short_abund  // tuple(meta, tsv); empty on long-only platforms
    long_abundance  = ch_long_abund   // tuple(meta, tsv); empty on illumina
}
