/*
 * PacBio HiFi platform subworkflow (DAG platform_resolution.pacbio_hifi):
 * [BAM→FASTQ | provided FASTQ] → HiFiAdapterFilt → [minimap2 host removal] →
 * hifiasm-meta → QUAST → contig coverage → plasmid detection/consensus →
 * downstream → abundance → host prediction → MAG → linking → comparative.
 */
include { SAMTOOLS_FASTQ } from '../modules/basecalling/samtools_fastq'
include { HIFIADAPTERFILT } from '../modules/qc/hifiadapterfilt'
include { MULTIQC } from '../modules/qc/multiqc'
include { MINIMAP2_HOST_REMOVAL } from '../modules/host_removal/minimap2_host'
include { HIFIASM_META } from '../modules/assembly/hifiasm_meta'
include { QUAST } from '../modules/assembly_qc/quast'
include { CONTIG_COVERAGE } from './contig_coverage'
include { PLASMID_DETECTION } from './plasmid_detection'
include { PLASMID_DOWNSTREAM } from './plasmid_downstream'
include { PLASMID_ABUNDANCE } from './plasmid_abundance'
include { HOST_PREDICTION } from './host_prediction'
include { MAG_HOST } from './mag_host'
include { HOST_LINKING } from './host_linking'
include { COMPARATIVE } from './comparative'

workflow PACBIO_HIFI {
    take:
    ch_samples // tuple(meta, bam, long_reads)

    main:
    // ---------------- long-read input (00) ----------------
    ch_br = ch_samples.branch { meta, bam, lr ->
        bam: bam != null
        fastq: true
    }
    SAMTOOLS_FASTQ(ch_br.bam.map { meta, bam, lr -> tuple(meta, bam) })
    ch_long_raw = ch_br.fastq.map { meta, bam, lr -> tuple(meta, lr) }
        .mix(SAMTOOLS_FASTQ.out.long_reads)

    // ---------------- QC (01) ----------------
    HIFIADAPTERFILT(ch_long_raw)

    // ---------------- host removal (optional) ----------------
    ch_hr = HIFIADAPTERFILT.out.reads.branch { meta, fq ->
        host: meta.host_reference != null
        nohost: true
    }
    MINIMAP2_HOST_REMOVAL(
        ch_hr.host.map { meta, fq -> tuple(meta, fq, file(meta.host_reference)) },
        'map-hifi'
    )
    ch_final_long = ch_hr.nohost.mix(MINIMAP2_HOST_REMOVAL.out.reads)

    // ---------------- assembly (02) ----------------
    HIFIASM_META(ch_final_long)
    ch_assembly = HIFIASM_META.out.assembly

    QUAST(ch_assembly)

    // ---------------- contig coverage ----------------
    CONTIG_COVERAGE(ch_assembly, Channel.empty(), ch_final_long, 'map-hifi')

    // ---------------- plasmid detection (04) ----------------
    PLASMID_DETECTION(ch_assembly, Channel.empty())
    ch_plasmids = PLASMID_DETECTION.out.plasmid_contigs.filter { meta, f -> f.size() > 0 }

    PLASMID_DOWNSTREAM(
        ch_plasmids, HIFIASM_META.out.graph, CONTIG_COVERAGE.out.bam,
        CONTIG_COVERAGE.out.table, Channel.empty()
    )

    // ---------------- abundance (10) ----------------
    PLASMID_ABUNDANCE(ch_plasmids, Channel.empty(), ch_final_long, 'map-hifi', false)

    HOST_PREDICTION(Channel.empty(), ch_final_long, ch_plasmids, false, false)
    MAG_HOST(ch_assembly, CONTIG_COVERAGE.out.bam, CONTIG_COVERAGE.out.table)
    HOST_LINKING(
        ch_plasmids, ch_assembly, CONTIG_COVERAGE.out.bam,
        PLASMID_ABUNDANCE.out.long_abundance, HOST_PREDICTION.out.host_profile,
        MAG_HOST.out.mag_bins, MAG_HOST.out.taxonomy, true
    )

    COMPARATIVE(ch_plasmids, PLASMID_DOWNSTREAM.out.bakta_dir)

    emit:
    plasmids       = ch_plasmids
    contig_tables  = CONTIG_COVERAGE.out.table
    plasmid_tables = PLASMID_ABUNDANCE.out.long_abundance
    done = PLASMID_DETECTION.out.consensus.map { meta, f -> f }
        .mix(PLASMID_DETECTION.out.structure.map { meta, f -> f })
        .mix(CONTIG_COVERAGE.out.table.map { meta, f -> f })
        .mix(PLASMID_ABUNDANCE.out.long_abundance.map { meta, f -> f })
        .mix(HOST_PREDICTION.out.host_profile.map { meta, f -> f })
        .mix(QUAST.out.report.map { meta, f -> f })
}
