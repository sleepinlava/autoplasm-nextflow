/*
 * ONT platform subworkflow (DAG platform_resolution.ont):
 * [Dorado basecalling | BAM→FASTQ | provided FASTQ] → NanoPlot + Filtlong →
 * [minimap2 host removal] → metaFlye → [medaka polishing] → QUAST →
 * contig coverage → plasmid detection/consensus → downstream → abundance →
 * host prediction → MAG → linking (incl. long-read bridge) → comparative.
 */
include { DORADO_BASECALL } from '../modules/basecalling/dorado'
include { SAMTOOLS_FASTQ } from '../modules/basecalling/samtools_fastq'
include { NANOPLOT } from '../modules/qc/nanoplot'
include { FILTLONG } from '../modules/qc/filtlong'
include { MULTIQC } from '../modules/qc/multiqc'
include { MINIMAP2_HOST_REMOVAL } from '../modules/host_removal/minimap2_host'
include { METAFLYE } from '../modules/assembly/metaflye'
include { MEDAKA } from '../modules/polishing/medaka'
include { QUAST } from '../modules/assembly_qc/quast'
include { CONTIG_COVERAGE } from './contig_coverage'
include { PLASMID_DETECTION } from './plasmid_detection'
include { PLASMID_DOWNSTREAM } from './plasmid_downstream'
include { PLASMID_ABUNDANCE } from './plasmid_abundance'
include { HOST_PREDICTION } from './host_prediction'
include { MAG_HOST } from './mag_host'
include { HOST_LINKING } from './host_linking'
include { COMPARATIVE } from './comparative'

workflow ONT {
    take:
    ch_samples // tuple(meta, pod5, bam, long_reads)

    main:
    // ---------------- basecalling / long-read input (00) ----------------
    ch_br = ch_samples.branch { meta, pod5, bam, lr ->
        pod5: pod5 != null
        bam: bam != null
        fastq: true
    }
    DORADO_BASECALL(ch_br.pod5.map { meta, pod5, bam, lr -> tuple(meta, pod5) })
    SAMTOOLS_FASTQ(ch_br.bam.map { meta, pod5, bam, lr -> tuple(meta, bam) })
    ch_long_raw = ch_br.fastq.map { meta, pod5, bam, lr -> tuple(meta, lr) }
        .mix(DORADO_BASECALL.out.long_reads, SAMTOOLS_FASTQ.out.long_reads)

    // ---------------- QC (01) ----------------
    NANOPLOT(ch_long_raw)
    FILTLONG(ch_long_raw)

    // ---------------- host removal (optional) ----------------
    ch_hr = FILTLONG.out.reads.branch { meta, fq ->
        host: meta.host_reference != null
        nohost: true
    }
    MINIMAP2_HOST_REMOVAL(
        ch_hr.host.map { meta, fq -> tuple(meta, fq, file(meta.host_reference)) },
        'map-ont'
    )
    ch_final_long = ch_hr.nohost.mix(MINIMAP2_HOST_REMOVAL.out.reads)

    // ---------------- assembly (02) + optional medaka polishing ----------------
    METAFLYE(ch_final_long)
    ch_assembly = METAFLYE.out.assembly
    if (params.polishing_tools.contains('medaka')) {
        MEDAKA(METAFLYE.out.assembly.join(ch_final_long))
        ch_assembly = MEDAKA.out.assembly
    }

    QUAST(ch_assembly)

    // ---------------- contig coverage ----------------
    CONTIG_COVERAGE(ch_assembly, Channel.empty(), ch_final_long, 'map-ont')

    // ---------------- plasmid detection (04) ----------------
    PLASMID_DETECTION(ch_assembly, Channel.empty())
    ch_plasmids = PLASMID_DETECTION.out.plasmid_contigs.filter { meta, f -> f.size() > 0 }

    PLASMID_DOWNSTREAM(
        ch_plasmids, METAFLYE.out.graph, CONTIG_COVERAGE.out.bam,
        CONTIG_COVERAGE.out.table, Channel.empty()
    )

    // ---------------- abundance (10) ----------------
    PLASMID_ABUNDANCE(ch_plasmids, Channel.empty(), ch_final_long, 'map-ont', false)

    // ---------------- host prediction / MAG / linking ----------------
    HOST_PREDICTION(Channel.empty(), ch_final_long, ch_plasmids, false, false)
    MAG_HOST(ch_assembly, CONTIG_COVERAGE.out.bam, CONTIG_COVERAGE.out.table)
    HOST_LINKING(
        ch_plasmids, ch_assembly, CONTIG_COVERAGE.out.long_bam,
        PLASMID_ABUNDANCE.out.long_abundance, HOST_PREDICTION.out.host_profile,
        MAG_HOST.out.mag_bins, MAG_HOST.out.taxonomy, true
    )

    COMPARATIVE(ch_plasmids, PLASMID_DOWNSTREAM.out.bakta_dir)

    if (params.run_multiqc) {
        // Preserve sample directories: each contains the same report basename.
        MULTIQC(NANOPLOT.out.report_dir.map { meta, dir -> dir }.collect(), 'multiqc_ont')
    }

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
