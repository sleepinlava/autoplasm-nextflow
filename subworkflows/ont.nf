include { LONG_READ_HOST_REMOVAL } from './long_read_host_removal'
include { reportEvidence; reportSamples } from '../lib/report_events'
include { selectedTools } from '../lib/tool_selection'

/*
 * ONT platform subworkflow (platform: ont):
 * [Dorado basecalling | BAM→FASTQ | provided FASTQ] → NanoPlot + Filtlong →
 * [minimap2 host removal] → metaFlye → [medaka polishing] → QUAST →
 * contig coverage → plasmid detection/consensus → downstream → abundance →
 * host prediction → MAG → linking (incl. long-read bridge) → comparative.
 *
 * QC/basecalling/assembly modules are the vendored nf-core ones; their
 * publish layout replicates the retired local modules via
 * conf/nfcore_qc_assembly.config.
 */
include { DORADO_BASECALL } from '../modules/basecalling/dorado'
include { SAMTOOLS_FASTQ } from '../modules/nf-core/samtools/fastq/main'
include { NANOPLOT } from '../modules/nf-core/nanoplot/main'
include { FILTLONG } from '../modules/nf-core/filtlong/main'
include { MULTIQC } from '../modules/nf-core/multiqc/main'
include { FLYE as METAFLYE } from '../modules/nf-core/flye/main'
include { MEDAKA; MEDAKA_RESOURCE_PROBE } from '../modules/nf-core/medaka/main'
include { medakaResourceRecord } from '../lib/medaka_runtime'
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

workflow ONT {
    take:
    ch_samples // tuple(meta, pod5, bam, long_reads)

    main:
    ch_report_events = Channel.empty()
    // ---------------- basecalling / long-read input (00) ----------------
    ch_br = ch_samples.branch { meta, pod5, bam, lr ->
        pod5: pod5 != null
        bam: bam != null
        fastq: true
    }
    DORADO_BASECALL(ch_br.pod5.map { meta, pod5, bam, lr -> tuple(meta, pod5) })
    ch_report_events = ch_report_events.mix(reportEvidence([channels: DORADO_BASECALL.out], '00_basecalling', 'DORADO_BASECALL'))
    // Long-read BAMs carry unpaired records: samtools fastq buckets them into
    // the -0 "other" output (nf-core module naming: <prefix>_other.fastq.gz).
    SAMTOOLS_FASTQ(ch_br.bam.map { meta, pod5, bam, lr -> tuple(meta, bam) }, false)
    ch_report_events = ch_report_events.mix(reportEvidence([channels: SAMTOOLS_FASTQ.out], '01_qc', 'SAMTOOLS_FASTQ'))
    ch_long_raw = ch_br.fastq.map { meta, pod5, bam, lr -> tuple(meta, lr) }
        .mix(DORADO_BASECALL.out.long_reads, SAMTOOLS_FASTQ.out.other)

    // ---------------- QC (01) ----------------
    NANOPLOT(ch_long_raw)
    ch_report_events = ch_report_events.mix(reportEvidence([channels: NANOPLOT.out], '01_qc', 'NANOPLOT'))
    FILTLONG(ch_long_raw.map { meta, fq -> tuple(meta, [], fq) })
    ch_report_events = ch_report_events.mix(reportEvidence([channels: FILTLONG.out], '01_qc', 'FILTLONG'))

    // ---------------- host removal (optional) ----------------
    LONG_READ_HOST_REMOVAL(FILTLONG.out.reads, 'map-ont')
    ch_final_long = LONG_READ_HOST_REMOVAL.out.reads
    ch_report_events = ch_report_events.mix(LONG_READ_HOST_REMOVAL.out.report_events)

    // ---------------- assembly (02) + optional medaka polishing ----------------
    METAFLYE(ch_final_long, '--nano-raw')
    ch_report_events = ch_report_events.mix(reportEvidence([channels: METAFLYE.out], '02_assembly', 'METAFLYE'))
    ch_assembly = METAFLYE.out.fasta
    if (selectedTools(params.polishing_tools).contains('medaka')) {
        ch_medaka_inputs = ch_final_long.join(METAFLYE.out.fasta,failOnDuplicate:true,failOnMismatch:true)
        ch_medaka_helpers = Channel.value(['medaka_runtime_resources.py','medaka_model_resources.py',
                                          'medaka_model_selection.py','medaka_index_resources.py'].collect {
            file("${moduleDir}/../bin/${it}",checkIfExists:true)
        })
        MEDAKA_RESOURCE_PROBE(ch_medaka_inputs,ch_medaka_helpers)
        ch_report_events = ch_report_events.mix(reportEvidence([channels: MEDAKA_RESOURCE_PROBE.out], '02_assembly', 'MEDAKA_RESOURCE_PROBE'))
        ch_medaka_identity = MEDAKA_RESOURCE_PROBE.out.identity.map { meta,receipt -> medakaResourceRecord(meta,receipt) }
        MEDAKA(ch_medaka_inputs.join(ch_medaka_identity,failOnDuplicate:true,failOnMismatch:true),ch_medaka_helpers)
        ch_report_events = ch_report_events.mix(reportEvidence([channels: MEDAKA.out], '02_assembly', 'MEDAKA'))
        ch_assembly = MEDAKA.out.assembly
    }

    QUAST(ch_assembly.map { meta, fasta -> tuple(meta, [fasta]) },
        Channel.value([[:], []]), Channel.value([[:], []]))
    ch_report_events = ch_report_events.mix(reportEvidence([channels: QUAST.out], '03_assembly_qc', 'QUAST'))

    // ---------------- contig coverage ----------------
    CONTIG_COVERAGE(ch_assembly, Channel.empty(), ch_final_long, 'map-ont')
    ch_report_events = ch_report_events.mix(CONTIG_COVERAGE.out.report_events)

    // ---------------- plasmid detection (04) ----------------
    PLASMID_DETECTION(ch_assembly)
    ch_report_events = ch_report_events.mix(PLASMID_DETECTION.out.report_events)
    ch_plasmids = PLASMID_DETECTION.out.plasmid_contigs.filter { meta, f -> f.size() > 0 }

    PLASMID_DOWNSTREAM(
        ch_plasmids, METAFLYE.out.gfa, CONTIG_COVERAGE.out.bam,
        CONTIG_COVERAGE.out.table, Channel.empty(), Channel.empty()
    )
    ch_report_events = ch_report_events.mix(PLASMID_DOWNSTREAM.out.report_events)

    // ---------------- abundance (10) ----------------
    PLASMID_ABUNDANCE(ch_plasmids, Channel.empty(), ch_final_long, 'map-ont', false)
    ch_report_events = ch_report_events.mix(PLASMID_ABUNDANCE.out.report_events)

    // ---------------- host prediction / MAG / linking ----------------
    HOST_PREDICTION(Channel.empty(), ch_final_long, ch_plasmids, false, false)
    ch_report_events = ch_report_events.mix(HOST_PREDICTION.out.report_events)
    MAG_HOST(ch_assembly, CONTIG_COVERAGE.out.bam, CONTIG_COVERAGE.out.table)
    ch_report_events = ch_report_events.mix(MAG_HOST.out.report_events)
    // All samples remap to one competitive nucleotide reference for statistics.
    // Include zero-candidate samples; local coverage remains for MAG/linking.
    SHARED_QUANTIFICATION(ch_assembly, PLASMID_DETECTION.out.plasmid_contigs,
                          Channel.empty(), ch_final_long, 'map-ont', ch_samples.count())
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
        // NanoPlot writes one report set per sample task; stage every HTML/TXT
        // into the MultiQC input so per-sample reports stay distinguishable.
        ch_nanoplot_qc = NANOPLOT.out.html
            .mix(NANOPLOT.out.txt)
            .map { meta, files -> files }
            .flatten()
            .collect()
        MULTIQC(ch_nanoplot_qc.map { files -> tuple([id: 'multiqc_ont'], files, [], [], [], []) })
        ch_report_events = ch_report_events.mix(reportEvidence([channels: MULTIQC.out], '01_qc', 'MULTIQC'))
    }

    emit:
    report_events = ch_report_events
    plasmids       = ch_plasmids
    contig_tables  = SHARED_QUANTIFICATION.out.contigs
    plasmid_tables = SHARED_QUANTIFICATION.out.plasmids
    quantification_states = SHARED_QUANTIFICATION.out.states
    done = ch_report_events
}
