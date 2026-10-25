include { reportEvidence; reportSamples } from '../lib/report_events'
/* Cross-sample measurements: one DNA reference, one read technology per sample.
 * Local per-sample coverage remains separate for MAG and host linking.
 */
include { SHARED_CATALOGUE } from '../modules/cross_sample/shared_catalogue'
include { SHARED_ABUNDANCE_TABLES } from '../modules/cross_sample/shared_abundance'
include { BOWTIE2_BUILD as BOWTIE2_BUILD_SHARED } from '../modules/nf-core/bowtie2/build/main'
include { BOWTIE2_ALIGN as BOWTIE2_ALIGN_SHARED } from '../modules/nf-core/bowtie2/align/main'
include { MINIMAP2_ALIGN as MINIMAP2_ALIGN_SHARED } from '../modules/nf-core/minimap2/align/main'
include { SAMTOOLS_VIEW as SAMTOOLS_VIEW_SHARED } from '../modules/nf-core/samtools/view/main'
include { COVERM_CONTIG as COVERM_SHARED } from '../modules/nf-core/coverm/contig/main'

workflow SHARED_QUANTIFICATION {
    take:
    ch_assemblies   // tuple(meta, fasta); exactly one per expected sample
    ch_plasmids     // tuple(meta, candidate fasta), including empty results
    ch_short_reads  // tuple(meta, r1, r2); used for Illumina AND hybrid
    ch_long_reads   // tuple(meta, reads); used only for long-only platforms
    read_mode      // short, map-ont or map-hifi
    n_samples

    main:
    ch_report_events = Channel.empty()
    if (!(read_mode in ['short', 'map-ont', 'map-hifi'])) {
        error "Unsupported shared-reference read mode: ${read_mode}"
    }
    ch_sources = ch_assemblies.map { meta, f -> tuple(meta.id, meta, f) }
        .join(ch_plasmids.map { meta, f -> tuple(meta.id, meta, f) }, failOnDuplicate: true, failOnMismatch: true)
        .toList().map { entries ->
            entries = entries.sort { it[0] }
            entries.each { entry -> if (entry[1] != entry[3]) error "Shared catalogue metadata mismatch: ${entry[0]}" }
            tuple(entries.collect { it[0] }, entries.collect { it[2] }, entries.collect { it[4] })
        }
    SHARED_CATALOGUE(ch_sources, n_samples, [file("${moduleDir}/../bin/build_shared_catalogue.py",checkIfExists:true)])
    ch_report_events = ch_report_events.mix(reportEvidence([channels: SHARED_CATALOGUE.out], '10_abundance', 'SHARED_CATALOGUE'))
    ch_catalogue = SHARED_CATALOGUE.out.catalogue.first()
    ch_reference = ch_catalogue.filter { dir -> dir.resolve('reference.fasta').size() > 0 }
        .map { dir -> tuple([id: 'shared_reference'], dir.resolve('reference.fasta')) }.first()
    ch_mapped = Channel.empty()
    if (read_mode == 'short') {
        BOWTIE2_BUILD_SHARED(ch_reference)
        ch_report_events = ch_report_events.mix(reportEvidence([channels: BOWTIE2_BUILD_SHARED.out], '10_abundance', 'BOWTIE2_BUILD_SHARED'))
        BOWTIE2_ALIGN_SHARED(
            ch_short_reads.map { meta, r1, r2 -> tuple(meta, [r1, r2]) },
            BOWTIE2_BUILD_SHARED.out.index.first(), ch_reference, false, true
        )
        ch_report_events = ch_report_events.mix(reportEvidence([channels: BOWTIE2_ALIGN_SHARED.out], '10_abundance', 'BOWTIE2_ALIGN_SHARED'))
        ch_mapped = BOWTIE2_ALIGN_SHARED.out.bam
    } else {
        MINIMAP2_ALIGN_SHARED(
            ch_long_reads.map { meta, reads -> tuple(meta + [preset: read_mode], reads) },
            ch_reference, true, '', false, false
        )
        ch_report_events = ch_report_events.mix(reportEvidence([channels: MINIMAP2_ALIGN_SHARED.out], '10_abundance', 'MINIMAP2_ALIGN_SHARED'))
        ch_mapped = MINIMAP2_ALIGN_SHARED.out.bam
    }
    SAMTOOLS_VIEW_SHARED(ch_mapped.map { meta, bam -> tuple(meta, bam, []) },
                         [[], [], []], [[], []], [[], []], '')
    ch_report_events = ch_report_events.mix(reportEvidence([channels: SAMTOOLS_VIEW_SHARED.out], '10_abundance', 'SAMTOOLS_VIEW_SHARED'))
    COVERM_SHARED(SAMTOOLS_VIEW_SHARED.out.bam, [[], []], true, false, false)
    ch_report_events = ch_report_events.mix(reportEvidence([channels: COVERM_SHARED.out], '10_abundance', 'COVERM_SHARED'))
    ch_tables = COVERM_SHARED.out.coverage.toList().map { entries ->
        tuple(entries.collect { it[0].id }, entries.collect { it[1] })
    }
    SHARED_ABUNDANCE_TABLES(ch_catalogue, ch_tables, read_mode == 'short' ? 'bowtie2' : 'minimap2',
        [file("${moduleDir}/../bin/collect_shared_abundance.py",checkIfExists:true)])
    ch_report_events = ch_report_events.mix(reportEvidence([channels: SHARED_ABUNDANCE_TABLES.out], '10_abundance', 'SHARED_ABUNDANCE_TABLES'))

    emit:
    report_events = ch_report_events
    contigs = SHARED_ABUNDANCE_TABLES.out.contigs
    plasmids = SHARED_ABUNDANCE_TABLES.out.plasmids
    states = SHARED_ABUNDANCE_TABLES.out.states
    method = SHARED_ABUNDANCE_TABLES.out.method
    catalogue = ch_catalogue
}
