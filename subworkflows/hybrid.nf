include { LONG_READ_HOST_REMOVAL } from './long_read_host_removal'
include { reportEvidence; reportSamples } from '../lib/report_events'
/*
 * Hybrid platform subworkflow (platform: hybrid): short reads
 * go through fastp (+ optional bowtie2 host removal), long reads through
 * NanoPlot/Filtlong (+ optional minimap2 host removal); assembly with
 * OPERA-MS (default) or hybridSPAdes; both mappers feed contig coverage
 * (BAMs merged); plasmid abundance runs a short and a long chain.
 *
 * QC/basecalling/assembly modules are the vendored nf-core ones; their
 * publish layout replicates the retired local modules via
 * conf/nfcore_qc_assembly.config.
 */
include { DORADO_BASECALL } from '../modules/basecalling/dorado'
include { SAMTOOLS_FASTQ } from '../modules/nf-core/samtools/fastq/main'
include { FASTP } from '../modules/nf-core/fastp/main'
include { FASTQC; FASTQC as FASTQC_CLEAN } from '../modules/nf-core/fastqc/main'
include { NANOPLOT } from '../modules/nf-core/nanoplot/main'
include { FILTLONG } from '../modules/nf-core/filtlong/main'
include { MULTIQC; MULTIQC as MULTIQC_ONT } from '../modules/nf-core/multiqc/main'
include { SHORT_READ_MULTIQC_INPUTS } from './short_read_multiqc_inputs'
include { BOWTIE2_BUILD as BOWTIE2_BUILD_HOST } from '../modules/nf-core/bowtie2/build/main'
include { BOWTIE2_ALIGN as BOWTIE2_ALIGN_HOST } from '../modules/nf-core/bowtie2/align/main'
include { OPERA_MS } from '../modules/assembly/opera_ms'
include { SPADES as HYBRIDSPADES } from '../modules/nf-core/spades/main'
include { QUAST } from '../modules/nf-core/quast/main'
include { CONTIG_COVERAGE } from './contig_coverage'
include { PLASMID_DETECTION } from './plasmid_detection'
include { GPLAS_BINNING } from './gplas_binning'
include { PLASMID_DOWNSTREAM } from './plasmid_downstream'
include { PLASMID_ABUNDANCE } from './plasmid_abundance'
include { SHARED_QUANTIFICATION } from './shared_quantification'
include { HOST_PREDICTION } from './host_prediction'
include { MAG_HOST } from './mag_host'
include { HOST_LINKING } from './host_linking'
include { COMPARATIVE } from './comparative'

workflow HYBRID {
    take:
    ch_samples // tuple(meta, read1, read2, pod5, bam, long_reads)

    main:
    ch_report_events = Channel.empty()
    // ---------------- short-read QC (01) ----------------
    ch_short = ch_samples.map { meta, r1, r2, pod5, bam, lr -> tuple(meta, r1, r2) }
    FASTP(ch_short.map { meta, r1, r2 -> tuple(meta, [r1, r2], []) }, false, false, false)
    ch_report_events = ch_report_events.mix(reportEvidence([channels: FASTP.out], '01_qc', 'FASTP'))
    ch_clean = FASTP.out.reads.map { meta, reads -> tuple(meta, reads[0], reads[1]) }
    if (params.run_fastqc) {
        FASTQC(ch_short.map { meta, r1, r2 -> tuple(meta + [stage: 'raw'], [r1, r2]) })
        ch_report_events = ch_report_events.mix(reportEvidence([channels: FASTQC.out], '01_qc', 'FASTQC'))
        FASTQC_CLEAN(ch_clean.map { meta, r1, r2 -> tuple(meta + [stage: 'clean'], [r1, r2]) })
        ch_report_events = ch_report_events.mix(reportEvidence([channels: FASTQC_CLEAN.out], '01_qc', 'FASTQC_CLEAN'))
    }
    ch_br = ch_clean.branch { meta, _r1, _r2 ->
        host: meta.host_reference != null
        nohost: true
    }
    ch_host_ref = ch_br.host.map { meta, _r1, _r2 -> tuple(meta, file(meta.host_reference)) }
    BOWTIE2_BUILD_HOST(ch_host_ref)
    ch_report_events = ch_report_events.mix(reportEvidence([channels: BOWTIE2_BUILD_HOST.out], '01_qc', 'BOWTIE2_BUILD_HOST'))
    ch_host_matched = ch_br.host.join(ch_host_ref,
        failOnDuplicate: true, failOnMismatch: true)
        .join(BOWTIE2_BUILD_HOST.out.index, failOnDuplicate: true, failOnMismatch: true)
    BOWTIE2_ALIGN_HOST(
        ch_host_matched.map { meta, r1, r2, _reference, _index -> tuple(meta, [r1, r2]) },
        ch_host_matched.map { meta, _r1, _r2, _reference, index -> tuple(meta, index) },
        ch_host_matched.map { meta, _r1, _r2, reference, _index -> tuple(meta, reference) },
        true,  // save_unaligned — the unmapped pairs are the host-free reads
        false  // sort_bam
    )
    ch_report_events = ch_report_events.mix(reportEvidence([channels: BOWTIE2_ALIGN_HOST.out], '01_qc', 'BOWTIE2_ALIGN_HOST'))
    ch_final_short = ch_br.nohost.mix(
        BOWTIE2_ALIGN_HOST.out.fastq.map { meta, fqs ->
            def pair = fqs in List ? fqs : [fqs]
            tuple(meta, pair[0], pair[1])
        }
    )

    // ---------------- long-read input + QC ----------------
    ch_long_in = ch_samples.map { meta, r1, r2, pod5, bam, lr -> tuple(meta, pod5, bam, lr) }
    ch_lb = ch_long_in.branch { meta, pod5, bam, lr ->
        pod5: pod5 != null
        bam: bam != null
        fastq: true
    }
    DORADO_BASECALL(ch_lb.pod5.map { meta, pod5, bam, lr -> tuple(meta, pod5) })
    ch_report_events = ch_report_events.mix(reportEvidence([channels: DORADO_BASECALL.out], '00_basecalling', 'DORADO_BASECALL'))
    // Long-read BAMs carry unpaired records: samtools fastq buckets them into
    // the -0 "other" output (nf-core module naming: <prefix>_other.fastq.gz).
    SAMTOOLS_FASTQ(ch_lb.bam.map { meta, pod5, bam, lr -> tuple(meta, bam) }, false)
    ch_report_events = ch_report_events.mix(reportEvidence([channels: SAMTOOLS_FASTQ.out], '01_qc', 'SAMTOOLS_FASTQ'))
    ch_long_raw = ch_lb.fastq.map { meta, pod5, bam, lr -> tuple(meta, lr) }
        .mix(DORADO_BASECALL.out.long_reads, SAMTOOLS_FASTQ.out.other)

    NANOPLOT(ch_long_raw)
    ch_report_events = ch_report_events.mix(reportEvidence([channels: NANOPLOT.out], '01_qc', 'NANOPLOT'))
    FILTLONG(ch_long_raw.map { meta, fq -> tuple(meta, [], fq) })
    ch_report_events = ch_report_events.mix(reportEvidence([channels: FILTLONG.out], '01_qc', 'FILTLONG'))

    LONG_READ_HOST_REMOVAL(FILTLONG.out.reads, 'map-ont')
    ch_final_long = LONG_READ_HOST_REMOVAL.out.reads
    ch_report_events = ch_report_events.mix(LONG_READ_HOST_REMOVAL.out.report_events)

    // ---------------- hybrid assembly (02) ----------------
    ch_asm_in = ch_final_short.join(ch_final_long)
    ch_recycler_graph = Channel.empty()
    ch_graph = Channel.empty()
    if (params.hybrid_assembler == 'hybridspades') {
        HYBRIDSPADES(ch_asm_in.map { meta, r1, r2, lr -> tuple(meta, [r1, r2], [], [lr]) }, [], [], Channel.value(file("${moduleDir}/../bin/spades_graph_provenance.py", checkIfExists: true)))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: HYBRIDSPADES.out], '02_assembly', 'HYBRIDSPADES'))
        ch_assembly = HYBRIDSPADES.out.contigs
        ch_recycler_graph = HYBRIDSPADES.out.recycler_graph
        ch_graph = HYBRIDSPADES.out.gplas_graph
    } else {
        OPERA_MS(ch_asm_in, Channel.value(file("${moduleDir}/../bin/validate_opera_ms_output.py", checkIfExists: true)))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: OPERA_MS.out], '02_assembly', 'OPERA_MS'))
        ch_assembly = OPERA_MS.out.assembly
    }

    GPLAS_BINNING(ch_assembly, ch_graph)
    ch_report_events = ch_report_events.mix(GPLAS_BINNING.out.report_events)

    QUAST(ch_assembly.map { meta, fasta -> tuple(meta, [fasta]) },
        Channel.value([[:], []]), Channel.value([[:], []]))
    ch_report_events = ch_report_events.mix(reportEvidence([channels: QUAST.out], '03_assembly_qc', 'QUAST'))

    // ---------------- contig coverage (both mappers, BAMs merged) ----------------
    CONTIG_COVERAGE(ch_assembly, ch_final_short, ch_final_long, 'map-ont')
    ch_report_events = ch_report_events.mix(CONTIG_COVERAGE.out.report_events)

    // ---------------- plasmid detection (04) ----------------
    PLASMID_DETECTION(ch_assembly)
    ch_report_events = ch_report_events.mix(PLASMID_DETECTION.out.report_events)
    ch_plasmids = PLASMID_DETECTION.out.plasmid_contigs.filter { meta, f -> f.size() > 0 }

    PLASMID_DOWNSTREAM(
        ch_plasmids, Channel.empty(), CONTIG_COVERAGE.out.bam,
        CONTIG_COVERAGE.out.table, ch_final_short, ch_recycler_graph
    )
    ch_report_events = ch_report_events.mix(PLASMID_DOWNSTREAM.out.report_events)

    // ---------------- abundance (10): short and long chains ----------------
    PLASMID_ABUNDANCE(ch_plasmids, ch_final_short, ch_final_long, 'map-ont', true)
    ch_report_events = ch_report_events.mix(PLASMID_ABUNDANCE.out.report_events)

    // ---------------- host prediction / MAG / linking ----------------
    HOST_PREDICTION(ch_final_short, Channel.empty(), ch_plasmids, false, false)
    ch_report_events = ch_report_events.mix(HOST_PREDICTION.out.report_events)
    MAG_HOST(ch_assembly, CONTIG_COVERAGE.out.bam, CONTIG_COVERAGE.out.table)
    ch_report_events = ch_report_events.mix(MAG_HOST.out.report_events)
    // All samples remap to one competitive nucleotide reference for statistics.
    // Include zero-candidate samples; local coverage remains for MAG/linking.
    SHARED_QUANTIFICATION(ch_assembly, PLASMID_DETECTION.out.plasmid_contigs,
                          ch_final_short, ch_final_long, 'short', ch_samples.count())
    ch_report_events = ch_report_events.mix(SHARED_QUANTIFICATION.out.report_events)

    HOST_LINKING(
        ch_plasmids, ch_assembly, CONTIG_COVERAGE.out.long_bam,
        SHARED_QUANTIFICATION.out.plasmids, HOST_PREDICTION.out.host_profile,
        MAG_HOST.out.mag_bins, MAG_HOST.out.taxonomy, true
    )
    ch_report_events = ch_report_events.mix(HOST_LINKING.out.report_events)

    COMPARATIVE(ch_plasmids, PLASMID_DOWNSTREAM.out.bakta_dir)
    ch_report_events = ch_report_events.mix(COMPARATIVE.out.report_events)

    if (params.run_multiqc) {
        ch_fastqc_raw = Channel.empty()
        ch_fastqc_clean = Channel.empty()
        if (params.run_fastqc) {
            ch_fastqc_raw = FASTQC.out.zip
            ch_fastqc_clean = FASTQC_CLEAN.out.zip
        }
        SHORT_READ_MULTIQC_INPUTS(FASTP.out.json, ch_fastqc_raw, ch_fastqc_clean, params.run_fastqc)
        MULTIQC(SHORT_READ_MULTIQC_INPUTS.out.files.map { files ->
            tuple([id: 'multiqc_illumina'], files, [], [], [], [])
        })
        ch_report_events = ch_report_events.mix(reportEvidence([channels: MULTIQC.out], '01_qc', 'MULTIQC'))
        // NanoPlot writes one report set per sample task; stage every HTML/TXT
        // into the MultiQC input so per-sample reports stay distinguishable.
        ch_nanoplot_qc = NANOPLOT.out.html
            .mix(NANOPLOT.out.txt)
            .map { meta, files -> files }
            .flatten()
            .collect()
        MULTIQC_ONT(ch_nanoplot_qc.map { files -> tuple([id: 'multiqc_ont'], files, [], [], [], []) })
        ch_report_events = ch_report_events.mix(reportEvidence([channels: MULTIQC_ONT.out], '01_qc', 'MULTIQC_ONT'))
    }

    emit:
    report_events = ch_report_events
    plasmids       = ch_plasmids
    contig_tables  = SHARED_QUANTIFICATION.out.contigs
    // Shared quantification uses only short reads for hybrid statistics
    plasmid_tables = SHARED_QUANTIFICATION.out.plasmids
    quantification_states = SHARED_QUANTIFICATION.out.states
    done = ch_report_events
}
