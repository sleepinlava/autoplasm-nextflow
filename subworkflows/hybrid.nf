/*
 * Hybrid platform subworkflow (DAG platform_resolution.hybrid): short reads
 * go through fastp (+ optional bowtie2 host removal), long reads through
 * NanoPlot/Filtlong (+ optional minimap2 host removal); assembly with
 * OPERA-MS (default) or hybridSPAdes; both mappers feed contig coverage
 * (BAMs merged); plasmid abundance runs a short and a long chain.
 */
include { DORADO_BASECALL } from '../modules/basecalling/dorado'
include { SAMTOOLS_FASTQ } from '../modules/basecalling/samtools_fastq'
include { FASTP } from '../modules/qc/fastp'
include { FASTQC; FASTQC as FASTQC_CLEAN } from '../modules/qc/fastqc'
include { NANOPLOT } from '../modules/qc/nanoplot'
include { FILTLONG } from '../modules/qc/filtlong'
include { MULTIQC; MULTIQC as MULTIQC_ONT } from '../modules/qc/multiqc'
include { SHORT_READ_MULTIQC_INPUTS } from './short_read_multiqc_inputs'
include { BOWTIE2_HOST_REMOVAL } from '../modules/host_removal/bowtie2_host'
include { MINIMAP2_HOST_REMOVAL } from '../modules/host_removal/minimap2_host'
include { OPERA_MS } from '../modules/assembly/opera_ms'
include { HYBRIDSPADES } from '../modules/assembly/hybridspades'
include { QUAST } from '../modules/assembly_qc/quast'
include { CONTIG_COVERAGE } from './contig_coverage'
include { PLASMID_DETECTION } from './plasmid_detection'
include { PLASMID_DOWNSTREAM } from './plasmid_downstream'
include { PLASMID_ABUNDANCE } from './plasmid_abundance'
include { HOST_PREDICTION } from './host_prediction'
include { MAG_HOST } from './mag_host'
include { HOST_LINKING } from './host_linking'
include { COMPARATIVE } from './comparative'

workflow HYBRID {
    take:
    ch_samples // tuple(meta, read1, read2, pod5, bam, long_reads)

    main:
    // ---------------- short-read QC (01) ----------------
    ch_short = ch_samples.map { meta, r1, r2, pod5, bam, lr -> tuple(meta, r1, r2) }
    FASTP(ch_short)
    if (params.run_fastqc) {
        FASTQC(ch_short.map { meta, r1, r2 -> tuple(meta, 'raw', r1, r2) })
        FASTQC_CLEAN(FASTP.out.reads.map { meta, r1, r2 -> tuple(meta, 'clean', r1, r2) })
    }
    ch_br = FASTP.out.reads.branch { meta, r1, r2 ->
        host: meta.host_reference != null
        nohost: true
    }
    BOWTIE2_HOST_REMOVAL(
        ch_br.host.map { meta, r1, r2 -> tuple(meta, r1, r2, file(meta.host_reference)) }
    )
    ch_final_short = ch_br.nohost.mix(BOWTIE2_HOST_REMOVAL.out.reads)

    // ---------------- long-read input + QC ----------------
    ch_long_in = ch_samples.map { meta, r1, r2, pod5, bam, lr -> tuple(meta, pod5, bam, lr) }
    ch_lb = ch_long_in.branch { meta, pod5, bam, lr ->
        pod5: pod5 != null
        bam: bam != null
        fastq: true
    }
    DORADO_BASECALL(ch_lb.pod5.map { meta, pod5, bam, lr -> tuple(meta, pod5) })
    SAMTOOLS_FASTQ(ch_lb.bam.map { meta, pod5, bam, lr -> tuple(meta, bam) })
    ch_long_raw = ch_lb.fastq.map { meta, pod5, bam, lr -> tuple(meta, lr) }
        .mix(DORADO_BASECALL.out.long_reads, SAMTOOLS_FASTQ.out.long_reads)

    NANOPLOT(ch_long_raw)
    FILTLONG(ch_long_raw)

    ch_hr = FILTLONG.out.reads.branch { meta, fq ->
        host: meta.host_reference != null
        nohost: true
    }
    MINIMAP2_HOST_REMOVAL(
        ch_hr.host.map { meta, fq -> tuple(meta, fq, file(meta.host_reference)) },
        'map-ont'
    )
    ch_final_long = ch_hr.nohost.mix(MINIMAP2_HOST_REMOVAL.out.reads)

    // ---------------- hybrid assembly (02) ----------------
    ch_asm_in = ch_final_short.join(ch_final_long)
    if (params.hybrid_assembler == 'hybridspades') {
        HYBRIDSPADES(ch_asm_in)
        ch_assembly = HYBRIDSPADES.out.assembly
    } else {
        OPERA_MS(ch_asm_in)
        ch_assembly = OPERA_MS.out.assembly
    }

    QUAST(ch_assembly)

    // ---------------- contig coverage (both mappers, BAMs merged) ----------------
    CONTIG_COVERAGE(ch_assembly, ch_final_short, ch_final_long, 'map-ont')

    // ---------------- plasmid detection (04) ----------------
    PLASMID_DETECTION(ch_assembly, Channel.empty())
    ch_plasmids = PLASMID_DETECTION.out.plasmid_contigs.filter { meta, f -> f.size() > 0 }

    PLASMID_DOWNSTREAM(
        ch_plasmids, Channel.empty(), CONTIG_COVERAGE.out.bam,
        CONTIG_COVERAGE.out.table, ch_final_short
    )

    // ---------------- abundance (10): short and long chains ----------------
    PLASMID_ABUNDANCE(ch_plasmids, ch_final_short, ch_final_long, 'map-ont', true)

    // ---------------- host prediction / MAG / linking ----------------
    HOST_PREDICTION(ch_final_short, Channel.empty(), ch_plasmids, false, false)
    MAG_HOST(ch_assembly, CONTIG_COVERAGE.out.bam, CONTIG_COVERAGE.out.table)
    HOST_LINKING(
        ch_plasmids, ch_assembly, CONTIG_COVERAGE.out.long_bam,
        PLASMID_ABUNDANCE.out.short_abundance, HOST_PREDICTION.out.host_profile,
        MAG_HOST.out.mag_bins, MAG_HOST.out.taxonomy, true
    )

    COMPARATIVE(ch_plasmids, PLASMID_DOWNSTREAM.out.bakta_dir)

    if (params.run_multiqc) {
        ch_fastqc_raw = Channel.empty()
        ch_fastqc_clean = Channel.empty()
        if (params.run_fastqc) {
            ch_fastqc_raw = FASTQC.out.results
            ch_fastqc_clean = FASTQC_CLEAN.out.results
        }
        SHORT_READ_MULTIQC_INPUTS(FASTP.out.json, ch_fastqc_raw, ch_fastqc_clean, params.run_fastqc)
        MULTIQC(SHORT_READ_MULTIQC_INPUTS.out.files, 'multiqc_illumina')
        MULTIQC_ONT(NANOPLOT.out.report_dir.map { meta, dir -> dir }.collect(), 'multiqc_ont')
    }

    emit:
    plasmids       = ch_plasmids
    contig_tables  = CONTIG_COVERAGE.out.table
    // Cross-sample statistics use the short-read abundance chain for hybrid
    plasmid_tables = PLASMID_ABUNDANCE.out.short_abundance
    done = PLASMID_DETECTION.out.consensus.map { meta, f -> f }
        .mix(PLASMID_DETECTION.out.structure.map { meta, f -> f })
        .mix(CONTIG_COVERAGE.out.table.map { meta, f -> f })
        .mix(PLASMID_ABUNDANCE.out.short_abundance.map { meta, f -> f })
        .mix(PLASMID_ABUNDANCE.out.long_abundance.map { meta, f -> f })
        .mix(HOST_PREDICTION.out.host_profile.map { meta, f -> f })
        .mix(QUAST.out.report.map { meta, f -> f })
}
