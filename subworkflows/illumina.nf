include { protocolAssets } from '../lib/protocol_assets'
include { reportEvidence; reportSamples } from '../lib/report_events'
/*
 * Illumina platform subworkflow (platform: illumina):
 * fastp → [fastqc] → [bowtie2 host removal] → MEGAHIT/metaSPAdes → QUAST →
 * contig coverage → plasmid detection/consensus → downstream (typing,
 * annotation, binning) → abundance → host prediction → MAG → linking →
 * comparative genomics.
 *
 * QC/basecalling/assembly modules are the vendored nf-core ones; their
 * publish layout replicates the retired local modules via
 * conf/nfcore_qc_assembly.config.
 */
include { FASTP } from '../modules/nf-core/fastp/main'
include { FASTQC; FASTQC as FASTQC_CLEAN } from '../modules/nf-core/fastqc/main'
include { MULTIQC } from '../modules/nf-core/multiqc/main'
include { SHORT_READ_MULTIQC_INPUTS } from './short_read_multiqc_inputs'
include { BOWTIE2_BUILD as BOWTIE2_BUILD_HOST } from '../modules/nf-core/bowtie2/build/main'
include { BOWTIE2_ALIGN as BOWTIE2_ALIGN_HOST } from '../modules/nf-core/bowtie2/align/main'
include { MEGAHIT } from '../modules/nf-core/megahit/main'
include { SPADES as METASPADES } from '../modules/nf-core/spades/main'
include { QUAST } from '../modules/nf-core/quast/main'
include { CONTIG_COVERAGE } from './contig_coverage'
include { PLASMID_DETECTION } from './plasmid_detection'
include { GPLAS_BINNING } from './gplas_binning'
include { PLASMAAG_BINNING } from './plasmaag_binning'
include { PLASMID_DOWNSTREAM } from './plasmid_downstream'
include { PLASMID_ABUNDANCE } from './plasmid_abundance'
include { SHARED_QUANTIFICATION } from './shared_quantification'
include { HOST_PREDICTION } from './host_prediction'
include { MAG_HOST } from './mag_host'
include { HOST_LINKING } from './host_linking'
include { PROTOCOL_INPUT_AUDIT; PROTOCOL_RETENTION; PROTOCOL_HOST_FILTER } from '../modules/protocol/input_audit'
include { SHORT_READ_PROTOCOL } from './short_read_protocol'
include { COMPARATIVE } from './comparative'

workflow ILLUMINA {
    take:
    ch_samples // tuple(meta, read1, read2)

    main:
    ch_report_events = Channel.empty()
    // ---------------- QC (01) ----------------
    FASTP(ch_samples.map { meta, r1, r2 -> tuple(meta, [r1, r2], []) }, false, false, false)
    ch_report_events = ch_report_events.mix(reportEvidence([channels: FASTP.out], '01_qc', 'FASTP'))
    ch_clean = FASTP.out.reads.map { meta, reads -> tuple(meta, reads[0], reads[1]) }

    if (params.run_fastqc) {
        FASTQC(ch_samples.map { meta, r1, r2 -> tuple(meta + [stage: 'raw'], [r1, r2]) })
        ch_report_events = ch_report_events.mix(reportEvidence([channels: FASTQC.out], '01_qc', 'FASTQC'))
        FASTQC_CLEAN(ch_clean.map { meta, r1, r2 -> tuple(meta + [stage: 'clean'], [r1, r2]) })
        ch_report_events = ch_report_events.mix(reportEvidence([channels: FASTQC_CLEAN.out], '01_qc', 'FASTQC_CLEAN'))
    }

    // ---------------- host removal (optional, per-sample reference) ----------------
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
    ch_final_reads = Channel.empty()
    if (params.short_read_protocol) {
        PROTOCOL_HOST_FILTER(BOWTIE2_ALIGN_HOST.out.bam.join(ch_host_ref,failOnDuplicate:true,failOnMismatch:true))
        ch_final_reads = ch_br.nohost.mix(PROTOCOL_HOST_FILTER.out.reads)
        ch_report_events = ch_report_events.mix(reportEvidence([channels:PROTOCOL_HOST_FILTER.out],'01_qc','PROTOCOL_HOST_FILTER'))
    } else {
    ch_final_reads = ch_br.nohost.mix(
        BOWTIE2_ALIGN_HOST.out.fastq.map { meta, fqs ->
            def pair = fqs in List ? fqs : [fqs]
            tuple(meta, pair[0], pair[1])
        }
    )
    }

    // ---------------- assembly (02) ----------------
    ch_assembly = Channel.empty()
    ch_graph = Channel.empty()
    ch_recycler_graph = Channel.empty()
    ch_plasmaag_bundle = Channel.empty()
    if (params.short_read_assembler == 'metaspades') {
        METASPADES(ch_final_reads.map { meta, r1, r2 -> tuple(meta, [r1, r2], [], []) }, [], [], Channel.value(file("${moduleDir}/../bin/spades_graph_provenance.py", checkIfExists: true)))
        ch_report_events = ch_report_events.mix(reportEvidence([channels: METASPADES.out], '02_assembly', 'METASPADES'))
        ch_assembly = METASPADES.out.contigs
        ch_graph = METASPADES.out.gplas_graph
        ch_recycler_graph = METASPADES.out.recycler_graph
        ch_plasmaag_bundle = METASPADES.out.plasmaag_assembly
    } else {
        MEGAHIT(ch_final_reads)
        ch_report_events = ch_report_events.mix(reportEvidence([channels: MEGAHIT.out], '02_assembly', 'MEGAHIT'))
        ch_assembly = MEGAHIT.out.contigs
    }

    PLASMAAG_BINNING(ch_assembly, ch_final_reads, ch_plasmaag_bundle)
    ch_report_events = ch_report_events.mix(PLASMAAG_BINNING.out.report_events)

    GPLAS_BINNING(ch_assembly, ch_graph)
    ch_report_events = ch_report_events.mix(GPLAS_BINNING.out.report_events)

    // ---------------- assembly QC (03) ----------------
    QUAST(ch_assembly.map { meta, fasta -> tuple(meta, [fasta]) },
        Channel.value([[:], []]), Channel.value([[:], []]))
    ch_report_events = ch_report_events.mix(reportEvidence([channels: QUAST.out], '03_assembly_qc', 'QUAST'))

    // ---------------- contig coverage (02/coverage) ----------------
    if (!params.short_read_protocol) {
        CONTIG_COVERAGE(ch_assembly, ch_final_reads, Channel.empty(), 'map-ont')
        ch_report_events = ch_report_events.mix(CONTIG_COVERAGE.out.report_events)
    }

    // ---------------- plasmid detection (04) ----------------
    PLASMID_DETECTION(ch_assembly)
    ch_report_events = ch_report_events.mix(PLASMID_DETECTION.out.report_events)
    ch_contig_tables = Channel.empty()
    ch_plasmid_tables = Channel.empty()
    ch_quantification_states = Channel.empty()
    ch_plasmids = Channel.empty()
    if (params.short_read_protocol) {
        PROTOCOL_INPUT_AUDIT(ch_samples, protocolAssets("${moduleDir}/../bin",'protocol_input_audit.py'))
        PROTOCOL_RETENTION(FASTP.out.json.join(ch_final_reads,failOnDuplicate:true,failOnMismatch:true), protocolAssets("${moduleDir}/../bin",'protocol_input_audit.py'))
        ch_report_events = ch_report_events.mix(reportEvidence([channels:PROTOCOL_INPUT_AUDIT.out],'01_qc','PROTOCOL_INPUT_AUDIT'),
            reportEvidence([channels:PROTOCOL_RETENTION.out],'01_qc','PROTOCOL_RETENTION'))
        ch_qc_evidence = PROTOCOL_INPUT_AUDIT.out.audit.mix(PROTOCOL_RETENTION.out.retention,PROTOCOL_HOST_FILTER.out.statistics,PROTOCOL_HOST_FILTER.out.reference_identity).map { meta,path -> path }
            .mix(PROTOCOL_INPUT_AUDIT.out.commands,PROTOCOL_RETENTION.out.commands,PROTOCOL_HOST_FILTER.out.commands,
                 ch_report_events.filter { record,files -> record.kind == 'runtime_command' }.flatMap { record,files -> files })
        SHORT_READ_PROTOCOL(ch_assembly, ch_final_reads, PLASMAAG_BINNING.out.bins,
            PLASMID_DETECTION.out.genomad_summary, PLASMID_DETECTION.out.structure,ch_qc_evidence,ch_report_events)
        ch_report_events = ch_report_events.mix(SHORT_READ_PROTOCOL.out.report_events)
        ch_plasmids = SHORT_READ_PROTOCOL.out.plasmids
        ch_contig_tables = SHORT_READ_PROTOCOL.out.contig_tables
        ch_plasmid_tables = SHORT_READ_PROTOCOL.out.plasmid_tables
        ch_quantification_states = SHORT_READ_PROTOCOL.out.states
    } else {
    // Skip samples whose consensus is empty so downstream tools never see
    // an empty FASTA
    ch_plasmids = PLASMID_DETECTION.out.plasmid_contigs.filter { meta, f -> f.size() > 0 }

    // ---------------- downstream: typing / annotation / binning ----------------
    PLASMID_DOWNSTREAM(
        ch_plasmids, ch_graph, CONTIG_COVERAGE.out.bam,
        CONTIG_COVERAGE.out.table, ch_final_reads, ch_recycler_graph
    )
    ch_report_events = ch_report_events.mix(PLASMID_DOWNSTREAM.out.report_events)

    // ---------------- abundance (10) ----------------
    PLASMID_ABUNDANCE(ch_plasmids, ch_final_reads, Channel.empty(), 'map-ont', false)
    ch_report_events = ch_report_events.mix(PLASMID_ABUNDANCE.out.report_events)

    // ---------------- host prediction (07) ----------------
    HOST_PREDICTION(ch_final_reads, Channel.empty(), ch_plasmids, true, false)
    ch_report_events = ch_report_events.mix(HOST_PREDICTION.out.report_events)

    // ---------------- MAG host genomes (07/mag) ----------------
    MAG_HOST(ch_assembly, CONTIG_COVERAGE.out.bam, CONTIG_COVERAGE.out.table)
    ch_report_events = ch_report_events.mix(MAG_HOST.out.report_events)

    // ---------------- host-plasmid linking (07) ----------------
    // All samples remap to one competitive nucleotide reference for statistics.
    // Include zero-candidate samples; local coverage remains for MAG/linking.
    SHARED_QUANTIFICATION(ch_assembly, PLASMID_DETECTION.out.plasmid_contigs,
                          ch_final_reads, Channel.empty(), 'short', ch_samples.count())
    ch_report_events = ch_report_events.mix(SHARED_QUANTIFICATION.out.report_events)

    HOST_LINKING(
        ch_plasmids, ch_assembly, Channel.empty(),
        SHARED_QUANTIFICATION.out.plasmids, HOST_PREDICTION.out.host_profile,
        MAG_HOST.out.mag_bins, MAG_HOST.out.taxonomy, false
    )
    ch_report_events = ch_report_events.mix(HOST_LINKING.out.report_events)

    // ---------------- comparative genomics (09) ----------------
    COMPARATIVE(ch_plasmids, PLASMID_DOWNSTREAM.out.bakta_dir)
    ch_report_events = ch_report_events.mix(COMPARATIVE.out.report_events)

        ch_contig_tables = SHARED_QUANTIFICATION.out.contigs
        ch_plasmid_tables = SHARED_QUANTIFICATION.out.plasmids
        ch_quantification_states = SHARED_QUANTIFICATION.out.states
    }

    // ---------------- MultiQC ----------------
    if (params.run_multiqc) {
        ch_fastqc_raw = Channel.empty()
        ch_fastqc_clean = Channel.empty()
        if (params.run_fastqc) {
            ch_fastqc_raw = FASTQC.out.zip
            ch_fastqc_clean = FASTQC_CLEAN.out.zip
        }
        SHORT_READ_MULTIQC_INPUTS(FASTP.out.json, ch_fastqc_raw, ch_fastqc_clean, params.run_fastqc)
        ch_qc_domain = ch_samples.map { meta,r1,r2 -> meta.id }.toSortedList().map { ids -> [samples:ids] }
        MULTIQC(SHORT_READ_MULTIQC_INPUTS.out.files.map { files -> [files:files] }.combine(ch_qc_domain).map { bundle,domain ->
            tuple([id: 'multiqc_illumina',cohort:true,cohort_samples:domain.samples], bundle.files, [], [], [], [])
        })
        ch_report_events = ch_report_events.mix(reportEvidence([channels: MULTIQC.out], '01_qc', 'MULTIQC'))
    }

    emit:
    report_events = ch_report_events
    plasmids       = ch_plasmids
    contig_tables  = ch_contig_tables
    plasmid_tables = ch_plasmid_tables
    quantification_states = ch_quantification_states
    done = ch_report_events
}
