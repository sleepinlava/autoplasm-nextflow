/*
 * Plasmid abundance subworkflow (DAG category abundance, 10): map reads to
 * the consensus plasmid contigs and estimate coverage with CoverM. Hybrid
 * samples run a short-read chain and a long-read chain in parallel
 * (abundance_*_short / abundance_*_long in the DAG).
 */
include { BOWTIE2_ABUNDANCE } from '../modules/abundance/bowtie2_abundance'
include { MINIMAP2_ABUNDANCE } from '../modules/abundance/minimap2_abundance'
include { SAMTOOLS_SORT } from '../modules/coverage/samtools_sort'
include { COVERM_ABUNDANCE } from '../modules/abundance/coverm_abundance'

workflow PLASMID_ABUNDANCE {
    take:
    ch_plasmids    // tuple(meta, plasmid_contigs.fasta)
    ch_short_reads // tuple(meta, r1, r2); empty when no short reads
    ch_long_reads  // tuple(meta, fastq); empty when no long reads
    long_preset    // val: minimap2 preset
    hybrid         // val: boolean — emit short/long labelled outputs

    main:
    def short_sub  = hybrid ? 'short' : ''
    def short_lbl  = hybrid ? '.short' : ''
    def long_sub   = hybrid ? 'long' : ''
    def long_lbl   = hybrid ? '.long' : ''

    ch_short_sam = BOWTIE2_ABUNDANCE(
        ch_plasmids.join(ch_short_reads)
            .map { meta, contigs, r1, r2 -> tuple(meta, contigs, r1, r2, short_sub, short_lbl) }
    ).alignment
    ch_long_sam = MINIMAP2_ABUNDANCE(
        ch_plasmids.join(ch_long_reads)
            .map { meta, contigs, lr -> tuple(meta, contigs, lr, long_sub, long_lbl) },
        long_preset
    ).alignment

    ch_short_bam = SAMTOOLS_SORT(
        ch_short_sam.map { meta, sam, sub, lbl ->
            tuple(meta, sam, "10_abundance/${meta.id}/${sub}", "${meta.id}${lbl}.bam") }
    ).bam
    ch_long_bam = SAMTOOLS_SORT(
        ch_long_sam.map { meta, sam, sub, lbl ->
            tuple(meta, sam, "10_abundance/${meta.id}/${sub}", "${meta.id}${lbl}.bam") }
    ).bam

    ch_short_abund = COVERM_ABUNDANCE(
        ch_short_bam.map { meta, bam -> tuple(meta, bam, short_sub, short_lbl) }
    ).abundance
    ch_long_abund = COVERM_ABUNDANCE(
        ch_long_bam.map { meta, bam -> tuple(meta, bam, long_sub, long_lbl) }
    ).abundance

    emit:
    short_abundance = ch_short_abund  // tuple(meta, tsv); empty on long-only platforms
    long_abundance  = ch_long_abund   // tuple(meta, tsv); empty on illumina
}
