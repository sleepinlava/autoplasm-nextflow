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
    FASTP(ch_samples.map { meta, r1, r2 -> tuple(meta, [r1, r2], []) }, false, false, false)
    ch_clean = FASTP.out.reads.map { meta, reads -> tuple(meta, reads[0], reads[1]) }

    if (params.run_fastqc) {
        FASTQC(ch_samples.map { meta, r1, r2 -> tuple(meta + [stage: 'raw'], [r1, r2]) })
        FASTQC_CLEAN(ch_clean.map { meta, r1, r2 -> tuple(meta + [stage: 'clean'], [r1, r2]) })
    }

    // ---------------- host removal (optional, per-sample reference) ----------------
    ch_br = ch_clean.branch { meta, _r1, _r2 ->
        host: meta.host_reference != null
        nohost: true
    }
    ch_host_ref = ch_br.host.map { meta, _r1, _r2 -> tuple(meta, file(meta.host_reference)) }
    BOWTIE2_BUILD_HOST(ch_host_ref)
    BOWTIE2_ALIGN_HOST(
        ch_br.host.map { meta, r1, r2 -> tuple(meta, [r1, r2]) },
        BOWTIE2_BUILD_HOST.out.index,
        ch_host_ref,
        true,  // save_unaligned — the unmapped pairs are the host-free reads
        false  // sort_bam
    )
    ch_final_reads = ch_br.nohost.mix(
        BOWTIE2_ALIGN_HOST.out.fastq.map { meta, fqs ->
            def pair = fqs in List ? fqs : [fqs]
            tuple(meta, pair[0], pair[1])
        }
    )

    // ---------------- assembly (02) ----------------
    ch_assembly = Channel.empty()
    ch_graph = Channel.empty()
    if (params.short_read_assembler == 'metaspades') {
        METASPADES(ch_final_reads.map { meta, r1, r2 -> tuple(meta, [r1, r2], [], []) }, [], [])
        ch_assembly = METASPADES.out.contigs
        ch_graph = METASPADES.out.fastg
    } else {
        MEGAHIT(ch_final_reads)
        ch_assembly = MEGAHIT.out.contigs
    }

    // ---------------- assembly QC (03) ----------------
    QUAST(ch_assembly.map { meta, fasta -> tuple(meta, [fasta]) },
        Channel.value([[:], []]), Channel.value([[:], []]))

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
        ch_plasmids, ch_assembly, Channel.empty(),
        PLASMID_ABUNDANCE.out.short_abundance, HOST_PREDICTION.out.host_profile,
        MAG_HOST.out.mag_bins, MAG_HOST.out.taxonomy, false
    )

    // ---------------- comparative genomics (09) ----------------
    COMPARATIVE(ch_plasmids, PLASMID_DOWNSTREAM.out.bakta_dir)

    // ---------------- MultiQC ----------------
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
        .mix(QUAST.out.tsv.map { meta, f -> f })
}
