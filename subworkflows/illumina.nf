/*
 * Illumina platform subworkflow (DAG platform_resolution.illumina):
 * fastp → [fastqc] → [bowtie2 host removal] → MEGAHIT/metaSPAdes → QUAST →
 * contig coverage → plasmid detection/consensus → downstream (typing,
 * annotation, binning) → abundance → host prediction → MAG → linking →
 * comparative genomics.
 */
include { FASTP } from '../modules/qc/fastp'
include { FASTQC; FASTQC as FASTQC_CLEAN } from '../modules/qc/fastqc'
include { MULTIQC } from '../modules/qc/multiqc'
include { BOWTIE2_HOST_REMOVAL } from '../modules/host_removal/bowtie2_host'
include { MEGAHIT } from '../modules/assembly/megahit'
include { METASPADES } from '../modules/assembly/metaspades'
include { QUAST } from '../modules/assembly_qc/quast'
include { CONTIG_COVERAGE } from './contig_coverage'
include { PLASMID_DETECTION } from './plasmid_detection'
include { PLASMID_DOWNSTREAM } from './plasmid_downstream'
include { PLASMID_ABUNDANCE } from './plasmid_abundance'
include { HOST_PREDICTION } from './host_prediction'
include { MAG_HOST } from './mag_host'
include { HOST_LINKING } from './host_linking'
include { COMPARATIVE } from './comparative'

workflow ILLUMINA {
    take:
    ch_samples // tuple(meta, read1, read2)

    main:
    // ---------------- QC (01) ----------------
    FASTP(ch_samples)
    ch_clean = FASTP.out.reads

    if (params.run_fastqc) {
        FASTQC(ch_samples.map { meta, r1, r2 -> tuple(meta, 'raw', r1, r2) })
        FASTQC_CLEAN(ch_clean.map { meta, r1, r2 -> tuple(meta, 'clean', r1, r2) })
    }

    // ---------------- host removal (optional, per-sample reference) ----------------
    ch_br = ch_clean.branch { meta, r1, r2 ->
        host: meta.host_reference != null
        nohost: true
    }
    BOWTIE2_HOST_REMOVAL(
        ch_br.host.map { meta, r1, r2 -> tuple(meta, r1, r2, file(meta.host_reference)) }
    )
    ch_final_reads = ch_br.nohost.mix(BOWTIE2_HOST_REMOVAL.out.reads)

    // ---------------- assembly (02) ----------------
    ch_assembly = Channel.empty()
    ch_graph = Channel.empty()
    if (params.short_read_assembler == 'metaspades') {
        METASPADES(ch_final_reads)
        ch_assembly = METASPADES.out.assembly
        ch_graph = METASPADES.out.graph
    } else {
        MEGAHIT(ch_final_reads)
        ch_assembly = MEGAHIT.out.assembly
    }

    // ---------------- assembly QC (03) ----------------
    QUAST(ch_assembly)

    // ---------------- contig coverage (02/coverage) ----------------
    CONTIG_COVERAGE(ch_assembly, ch_final_reads, Channel.empty(), 'map-ont')

    // ---------------- plasmid detection (04) ----------------
    // SCAPP detection needs the metaSPAdes graph + reads
    ch_scapp_reads = params.short_read_assembler == 'metaspades'
        ? ch_graph.join(ch_final_reads)
        : Channel.empty()
    PLASMID_DETECTION(ch_assembly, ch_scapp_reads)
    // Skip samples whose consensus is empty so downstream tools never see
    // an empty FASTA
    ch_plasmids = PLASMID_DETECTION.out.plasmid_contigs.filter { meta, f -> f.size() > 0 }

    // ---------------- downstream: typing / annotation / binning ----------------
    PLASMID_DOWNSTREAM(
        ch_plasmids, ch_graph, CONTIG_COVERAGE.out.bam,
        CONTIG_COVERAGE.out.table, ch_final_reads
    )

    // ---------------- abundance (10) ----------------
    PLASMID_ABUNDANCE(ch_plasmids, ch_final_reads, Channel.empty(), 'map-ont', false)

    // ---------------- host prediction (07) ----------------
    HOST_PREDICTION(ch_final_reads, Channel.empty(), ch_plasmids, true, false)

    // ---------------- MAG host genomes (07/mag) ----------------
    MAG_HOST(ch_assembly, CONTIG_COVERAGE.out.bam, CONTIG_COVERAGE.out.table)

    // ---------------- host-plasmid linking (07) ----------------
    HOST_LINKING(
        ch_plasmids, ch_assembly, CONTIG_COVERAGE.out.bam,
        PLASMID_ABUNDANCE.out.short_abundance, HOST_PREDICTION.out.host_profile,
        MAG_HOST.out.mag_bins, MAG_HOST.out.taxonomy, false
    )

    // ---------------- comparative genomics (09) ----------------
    COMPARATIVE(ch_plasmids, PLASMID_DOWNSTREAM.out.bakta_dir)

    // ---------------- MultiQC ----------------
    if (params.run_multiqc) {
        ch_qc_files = FASTP.out.json.map { meta, f -> f }
            .mix(FASTP.out.html.map { meta, f -> f })
        if (params.run_fastqc) {
            ch_qc_files = ch_qc_files
                .mix(FASTQC.out.results.map { meta, z, h -> [z, h] }.flatten())
                .mix(FASTQC_CLEAN.out.results.map { meta, z, h -> [z, h] }.flatten())
        }
        MULTIQC(ch_qc_files.collect(), 'multiqc_illumina')
    }

    emit:
    plasmids       = ch_plasmids
    contig_tables  = CONTIG_COVERAGE.out.table
    plasmid_tables = PLASMID_ABUNDANCE.out.short_abundance
    done = PLASMID_DETECTION.out.consensus.map { meta, f -> f }
        .mix(PLASMID_DETECTION.out.structure.map { meta, f -> f })
        .mix(CONTIG_COVERAGE.out.table.map { meta, f -> f })
        .mix(PLASMID_ABUNDANCE.out.short_abundance.map { meta, f -> f })
        .mix(HOST_PREDICTION.out.host_profile.map { meta, f -> f })
        .mix(QUAST.out.report.map { meta, f -> f })
}
