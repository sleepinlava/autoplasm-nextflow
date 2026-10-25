include { reportEvidence; reportSamples } from '../lib/report_events'
/*
 * Contig coverage subworkflow (contig_coverage): map reads to
 * the assembly and estimate coverage with CoverM. Short-read samples use
 * bowtie2 (index + align with sort_bam=true, so the sorted BAM comes straight
 * out of the aligner), long-read samples minimap2 (bam_format=true pipes
 * through samtools sort inside the module); hybrid runs both and merges the
 * BAMs with the nf-core samtools/merge. Chain labels ('.short'/'.long') ride
 * in meta.suffix so the published BAM names match the legacy layout; they are
 * stripped before the per-sample join/merge and before emit. Process names,
 * file names and publish dirs replicate the former local modules via
 * conf/nfcore_upstream.config.
 */
include { BOWTIE2_BUILD as BOWTIE2_BUILD_COVERAGE } from '../modules/nf-core/bowtie2/build/main'
include { BOWTIE2_ALIGN as BOWTIE2_ALIGN_COVERAGE } from '../modules/nf-core/bowtie2/align/main'
include { MINIMAP2_ALIGN as MINIMAP2_ALIGN_COVERAGE } from '../modules/nf-core/minimap2/align/main'
include { SAMTOOLS_MERGE } from '../modules/nf-core/samtools/merge/main'
include { COVERM_CONTIG } from '../modules/nf-core/coverm/contig/main'

// Drop the chain-label keys ('suffix'/'preset') that the wiring adds to meta
// before joining, merging, or emitting downstream.
def stripChainMeta(meta) {
    return meta.findAll { entry -> !(entry.key in ['suffix', 'preset']) }
}

workflow CONTIG_COVERAGE {
    take:
    ch_assembly    // tuple(meta, fasta)
    ch_short_reads // tuple(meta, r1, r2); empty when no short reads
    ch_long_reads  // tuple(meta, fastq); empty when no long reads
    long_preset    // val: minimap2 preset ('map-ont' or 'map-hifi')

    main:
    ch_report_events = Channel.empty()
    // ---- short-read chain: bowtie2 index build + align (sorted BAM) ----
    ch_short_in = ch_assembly.join(ch_short_reads)
        .map { meta, fasta, r1, r2 -> tuple(meta + [suffix: '.short'], fasta, r1, r2) }
    BOWTIE2_BUILD_COVERAGE(ch_short_in.map { meta, fasta, _r1, _r2 -> tuple(meta, fasta) })
    ch_report_events = ch_report_events.mix(reportEvidence([channels: BOWTIE2_BUILD_COVERAGE.out], '02_assembly', 'BOWTIE2_BUILD_COVERAGE'))
    // The asynchronous index must join its reads/reference before fan-out.
    ch_short_matched = ch_short_in.join(BOWTIE2_BUILD_COVERAGE.out.index,
        failOnDuplicate: true, failOnMismatch: true)
    BOWTIE2_ALIGN_COVERAGE(
        ch_short_matched.map { meta, _fasta, r1, r2, _index -> tuple(meta, [r1, r2]) },
        ch_short_matched.map { meta, _fasta, _r1, _r2, index -> tuple(meta, index) },
        ch_short_matched.map { meta, fasta, _r1, _r2, _index -> tuple(meta, fasta) },
        false, // save_unaligned
        true   // sort_bam
    )
    ch_report_events = ch_report_events.mix(reportEvidence([channels: BOWTIE2_ALIGN_COVERAGE.out], '02_assembly', 'BOWTIE2_ALIGN_COVERAGE'))
    ch_short_bam = BOWTIE2_ALIGN_COVERAGE.out.bam
        .map { meta, bam -> tuple(stripChainMeta(meta), bam) }

    // ---- long-read chain: minimap2 (sorted BAM via samtools sort pipe) ----
    ch_long_in = ch_assembly.join(ch_long_reads)
        .map { meta, fasta, lr -> tuple(meta + [suffix: '.long', preset: long_preset], fasta, lr) }
    MINIMAP2_ALIGN_COVERAGE(
        ch_long_in.map { meta, _fasta, lr -> tuple(meta, lr) },
        ch_long_in.map { meta, fasta, _lr -> tuple(meta, fasta) },
        true,  // bam_format
        '',    // bam_index_extension
        false, // cigar_paf_format
        false  // cigar_bam
    )
    ch_report_events = ch_report_events.mix(reportEvidence([channels: MINIMAP2_ALIGN_COVERAGE.out], '02_assembly', 'MINIMAP2_ALIGN_COVERAGE'))
    ch_long_bam = MINIMAP2_ALIGN_COVERAGE.out.bam
        .map { meta, bam -> tuple(stripChainMeta(meta), bam) }

    // Per-sample: merge when both mappers ran (hybrid), else pass through
    ch_per_sample = ch_short_bam.join(ch_long_bam, remainder: true)
        .map { meta, short_bam, long_bam ->
            def bams = [short_bam, long_bam].findAll { bam -> bam != null }
            tuple(meta, bams, []) // no BAM indexes to merge
        }
    ch_bam = SAMTOOLS_MERGE(ch_per_sample, [[], [], [], []], '').bam
    ch_report_events = ch_report_events.mix(reportEvidence([channels: SAMTOOLS_MERGE.out], '02_assembly', 'SAMTOOLS_MERGE'))

    ch_table = COVERM_CONTIG(ch_bam, [[], []], true, false, false).coverage
    ch_report_events = ch_report_events.mix(reportEvidence([channels: COVERM_CONTIG.out], '02_assembly', 'COVERM_CONTIG'))

    emit:
    report_events = ch_report_events
    bam      = ch_bam
    long_bam = ch_long_bam
    table    = ch_table
}
