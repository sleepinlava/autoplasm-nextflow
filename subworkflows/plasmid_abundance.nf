/*
 * Plasmid abundance subworkflow (DAG category abundance, 10): map reads to
 * the consensus plasmid contigs and estimate per-contig abundance with
 * CoverM. Hybrid samples run a short-read chain and a long-read chain in
 * parallel (abundance_*_short / abundance_*_long in the DAG); the chain label
 * ('.short'/'.long') rides in meta.suffix so the nf-core modules publish the
 * legacy file names (e.g. <id>.short.coverm.tsv) and is stripped again before
 * emit. Sorted BAMs come straight from the aligners (bowtie2 sort_bam=true;
 * minimap2 bam_format=true), replacing the former standalone samtools sort
 * steps. Process names, file names and publish dirs replicate the former
 * local modules via conf/nfcore_upstream.config.
 */
include { BOWTIE2_BUILD as BOWTIE2_BUILD_ABUNDANCE } from '../modules/nf-core/bowtie2/build/main'
include { BOWTIE2_ALIGN as BOWTIE2_ALIGN_ABUNDANCE } from '../modules/nf-core/bowtie2/align/main'
include { MINIMAP2_ALIGN as MINIMAP2_ALIGN_ABUNDANCE } from '../modules/nf-core/minimap2/align/main'
include { COVERM_CONTIG as COVERM_ABUNDANCE } from '../modules/nf-core/coverm/contig/main'
include { COVERM_CONTIG as COVERM_ABUNDANCE_LONG } from '../modules/nf-core/coverm/contig/main'

// Drop the chain-label keys ('suffix'/'preset') that the wiring adds to meta
// before CoverM output is emitted downstream.
def stripChainMeta(meta) {
    return meta.findAll { entry -> !(entry.key in ['suffix', 'preset']) }
}

workflow PLASMID_ABUNDANCE {
    take:
    ch_plasmids    // tuple(meta, plasmid_contigs.fasta)
    ch_short_reads // tuple(meta, r1, r2); empty when no short reads
    ch_long_reads  // tuple(meta, fastq); empty when no long reads
    long_preset    // val: minimap2 preset
    hybrid         // val: boolean — emit short/long labelled outputs

    main:
    // ---- short-read chain: bowtie2 index build + align (sorted BAM) ----
    ch_short_in = ch_plasmids.join(ch_short_reads)
        .map { meta, contigs, r1, r2 ->
            hybrid ? tuple(meta + [suffix: '.short'], contigs, r1, r2) : tuple(meta, contigs, r1, r2)
        }
    BOWTIE2_BUILD_ABUNDANCE(ch_short_in.map { meta, contigs, _r1, _r2 -> tuple(meta, contigs) })
    BOWTIE2_ALIGN_ABUNDANCE(
        ch_short_in.map { meta, _contigs, r1, r2 -> tuple(meta, [r1, r2]) },
        BOWTIE2_BUILD_ABUNDANCE.out.index,
        ch_short_in.map { meta, contigs, _r1, _r2 -> tuple(meta, contigs) },
        false, // save_unaligned
        true   // sort_bam
    )
    ch_short_abund = COVERM_ABUNDANCE(
        BOWTIE2_ALIGN_ABUNDANCE.out.bam,
        [[], []],
        true,  // bam_input
        false, // interleaved
        false  // enable_bam_output
    ).coverage.map { meta, tsv -> tuple(stripChainMeta(meta), tsv) }

    // ---- long-read chain: minimap2 (sorted BAM via samtools sort pipe) ----
    ch_long_in = ch_plasmids.join(ch_long_reads)
        .map { meta, contigs, lr -> tuple(meta + [suffix: hybrid ? '.long' : '', preset: long_preset], contigs, lr) }
    MINIMAP2_ALIGN_ABUNDANCE(
        ch_long_in.map { meta, _contigs, lr -> tuple(meta, lr) },
        ch_long_in.map { meta, contigs, _lr -> tuple(meta, contigs) },
        true,  // bam_format
        '',    // bam_index_extension
        false, // cigar_paf_format
        false  // cigar_bam
    )
    ch_long_abund = COVERM_ABUNDANCE_LONG(
        MINIMAP2_ALIGN_ABUNDANCE.out.bam,
        [[], []],
        true,  // bam_input
        false, // interleaved
        false  // enable_bam_output
    ).coverage.map { meta, tsv -> tuple(stripChainMeta(meta), tsv) }

    emit:
    short_abundance = ch_short_abund  // tuple(meta, tsv); empty on long-only platforms
    long_abundance  = ch_long_abund   // tuple(meta, tsv); empty on illumina
}
