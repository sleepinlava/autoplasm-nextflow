/*
 * Contig coverage subworkflow (DAG category contig_coverage): map reads to
 * the assembly, sort, and estimate coverage with CoverM. Short-read samples
 * use bowtie2, long-read samples minimap2; hybrid runs both and merges the
 * BAMs (mirroring the DAG's two contig mappers for hybrid).
 */
include { BOWTIE2_CONTIG_COVERAGE } from '../modules/coverage/bowtie2_contig'
include { MINIMAP2_CONTIG_COVERAGE } from '../modules/coverage/minimap2_contig'
include { SAMTOOLS_SORT; SAMTOOLS_SORT as SAMTOOLS_SORT_LONG; SAMTOOLS_MERGE } from '../modules/coverage/samtools_sort'
include { COVERM_CONTIG } from '../modules/coverage/coverm_contig'

workflow CONTIG_COVERAGE {
    take:
    ch_assembly    // tuple(meta, fasta)
    ch_short_reads // tuple(meta, r1, r2); empty when no short reads
    ch_long_reads  // tuple(meta, fastq); empty when no long reads
    long_preset    // val: minimap2 preset ('map-ont' or 'map-hifi')

    main:
    ch_short_bam = SAMTOOLS_SORT(
        BOWTIE2_CONTIG_COVERAGE(ch_assembly.join(ch_short_reads)).alignment
            .map { meta, sam -> tuple(meta, sam, "02_assembly/coverage/${meta.id}", "${meta.id}.contig_alignment.short.bam") }
    ).bam
    ch_long_bam = SAMTOOLS_SORT_LONG(
        MINIMAP2_CONTIG_COVERAGE(ch_assembly.join(ch_long_reads), long_preset).alignment
            .map { meta, sam -> tuple(meta, sam, "02_assembly/coverage/${meta.id}", "${meta.id}.contig_alignment.long.bam") }
    ).bam

    // Per-sample: merge when both mappers ran (hybrid), else pass through
    ch_per_sample = ch_short_bam.join(ch_long_bam, remainder: true)
        .map { meta, short_bam, long_bam ->
            def bams = [short_bam, long_bam].findAll { it != null }
            tuple(meta, bams)
        }
    ch_bam = SAMTOOLS_MERGE(
        ch_per_sample.map { meta, bams ->
            tuple(meta, bams, "02_assembly/coverage/${meta.id}", "${meta.id}.contig_alignment.bam")
        }
    ).bam

    ch_table = COVERM_CONTIG(ch_bam).table

    emit:
    bam   = ch_bam
    table = ch_table
}
