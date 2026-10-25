include { LONG_READ_HOST_REMOVAL } from './long_read_host_removal'
include { reportEvidence; reportSamples } from '../lib/report_events'
/*
 * PacBio HiFi platform subworkflow (platform: pacbio_hifi):
 * [BAM→FASTQ | provided FASTQ] → HiFiAdapterFilt → [minimap2 host removal] →
 * hifiasm-meta → QUAST → contig coverage → plasmid detection/consensus →
 * downstream → abundance → host prediction → MAG → linking → comparative.
 *
 * QC/basecalling modules are the vendored nf-core ones; their publish layout
 * replicates the retired local modules via conf/nfcore_qc_assembly.config.
 */
include { SAMTOOLS_FASTQ } from '../modules/nf-core/samtools/fastq/main'
include { HIFIADAPTERFILT_HIFIADAPTERFILT as HIFIADAPTERFILT } from '../modules/nf-core/hifiadapterfilt/hifiadapterfilt/main'
include { HIFIASM_META } from '../modules/assembly/hifiasm_meta'
include { QUAST } from '../modules/nf-core/quast/main'
include { CONTIG_COVERAGE } from './contig_coverage'
include { PLASMID_DETECTION } from './plasmid_detection'
include { PLASMID_DOWNSTREAM } from './plasmid_downstream'
include { PLASMID_ABUNDANCE } from './plasmid_abundance'
include { SHARED_QUANTIFICATION } from './shared_quantification'
include { HOST_PREDICTION } from './host_prediction'
include { MAG_HOST } from './mag_host'
include { HOST_LINKING } from './host_linking'
include { COMPARATIVE } from './comparative'

workflow PACBIO_HIFI {
    take:
    ch_samples // tuple(meta, bam, long_reads)

    main:
    ch_report_events = Channel.empty()
    // ---------------- long-read input (00) ----------------
    ch_br = ch_samples.branch { meta, bam, lr ->
        bam: bam != null
        fastq: true
    }
    // Long-read BAMs carry unpaired records: samtools fastq buckets them into
    // the -0 "other" output (nf-core module naming: <prefix>_other.fastq.gz).
    SAMTOOLS_FASTQ(ch_br.bam.map { meta, bam, lr -> tuple(meta, bam) }, false)
    ch_report_events = ch_report_events.mix(reportEvidence([channels: SAMTOOLS_FASTQ.out], '01_qc', 'SAMTOOLS_FASTQ'))
    ch_long_raw = ch_br.fastq.map { meta, bam, lr -> tuple(meta, lr) }
        .mix(SAMTOOLS_FASTQ.out.other)

    // ---------------- QC (01) ----------------
    // db=[]: the vendored module falls back to the adapter database shipped
    // with the hifiadapterfilt package itself (see the module's local patch).
    HIFIADAPTERFILT(ch_long_raw.map { meta, fq -> tuple(meta, fq, []) })
    ch_report_events = ch_report_events.mix(reportEvidence([channels: HIFIADAPTERFILT.out], '01_qc', 'HIFIADAPTERFILT'))
    ch_hifi_reads = HIFIADAPTERFILT.out.fastq

    // ---------------- host removal (optional) ----------------
    LONG_READ_HOST_REMOVAL(ch_hifi_reads, 'map-hifi')
    ch_final_long = LONG_READ_HOST_REMOVAL.out.reads
    ch_report_events = ch_report_events.mix(LONG_READ_HOST_REMOVAL.out.report_events)

    // ---------------- assembly (02) ----------------
    HIFIASM_META(ch_final_long)
    ch_report_events = ch_report_events.mix(reportEvidence([channels: HIFIASM_META.out], '02_assembly', 'HIFIASM_META'))
    ch_assembly = HIFIASM_META.out.assembly

    QUAST(ch_assembly.map { meta, fasta -> tuple(meta, [fasta]) },
        Channel.value([[:], []]), Channel.value([[:], []]))
    ch_report_events = ch_report_events.mix(reportEvidence([channels: QUAST.out], '03_assembly_qc', 'QUAST'))

    // ---------------- contig coverage ----------------
    CONTIG_COVERAGE(ch_assembly, Channel.empty(), ch_final_long, 'map-hifi')
    ch_report_events = ch_report_events.mix(CONTIG_COVERAGE.out.report_events)

    // ---------------- plasmid detection (04) ----------------
    PLASMID_DETECTION(ch_assembly)
    ch_report_events = ch_report_events.mix(PLASMID_DETECTION.out.report_events)
    ch_plasmids = PLASMID_DETECTION.out.plasmid_contigs.filter { meta, f -> f.size() > 0 }

    PLASMID_DOWNSTREAM(
        ch_plasmids, HIFIASM_META.out.graph, CONTIG_COVERAGE.out.bam,
        CONTIG_COVERAGE.out.table, Channel.empty(), Channel.empty()
    )
    ch_report_events = ch_report_events.mix(PLASMID_DOWNSTREAM.out.report_events)

    // ---------------- abundance (10) ----------------
    PLASMID_ABUNDANCE(ch_plasmids, Channel.empty(), ch_final_long, 'map-hifi', false)
    ch_report_events = ch_report_events.mix(PLASMID_ABUNDANCE.out.report_events)

    HOST_PREDICTION(Channel.empty(), ch_final_long, ch_plasmids, false, false)
    ch_report_events = ch_report_events.mix(HOST_PREDICTION.out.report_events)
    MAG_HOST(ch_assembly, CONTIG_COVERAGE.out.bam, CONTIG_COVERAGE.out.table)
    ch_report_events = ch_report_events.mix(MAG_HOST.out.report_events)
    // All samples remap to one competitive nucleotide reference for statistics.
    // Include zero-candidate samples; local coverage remains for MAG/linking.
    SHARED_QUANTIFICATION(ch_assembly, PLASMID_DETECTION.out.plasmid_contigs,
                          Channel.empty(), ch_final_long, 'map-hifi', ch_samples.count())
    ch_report_events = ch_report_events.mix(SHARED_QUANTIFICATION.out.report_events)

    HOST_LINKING(
        ch_plasmids, ch_assembly, CONTIG_COVERAGE.out.long_bam,
        SHARED_QUANTIFICATION.out.plasmids, HOST_PREDICTION.out.host_profile,
        MAG_HOST.out.mag_bins, MAG_HOST.out.taxonomy, true
    )
    ch_report_events = ch_report_events.mix(HOST_LINKING.out.report_events)

    COMPARATIVE(ch_plasmids, PLASMID_DOWNSTREAM.out.bakta_dir)
    ch_report_events = ch_report_events.mix(COMPARATIVE.out.report_events)

    emit:
    report_events = ch_report_events
    plasmids       = ch_plasmids
    contig_tables  = SHARED_QUANTIFICATION.out.contigs
    plasmid_tables = SHARED_QUANTIFICATION.out.plasmids
    quantification_states = SHARED_QUANTIFICATION.out.states
    done = ch_report_events
}
