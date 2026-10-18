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
include { MINIMAP2_ALIGN as MINIMAP2_ALIGN_HOST } from '../modules/nf-core/minimap2/align/main'
include { SAMTOOLS_VIEW as SAMTOOLS_VIEW_HOST } from '../modules/nf-core/samtools/view/main'
include { SAMTOOLS_FASTQ as SAMTOOLS_FASTQ_HOST } from '../modules/nf-core/samtools/fastq/main'
include { OPERA_MS } from '../modules/assembly/opera_ms'
include { SPADES as HYBRIDSPADES } from '../modules/nf-core/spades/main'
include { QUAST } from '../modules/nf-core/quast/main'
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
    FASTP(ch_short.map { meta, r1, r2 -> tuple(meta, [r1, r2], []) }, false, false, false)
    ch_clean = FASTP.out.reads.map { meta, reads -> tuple(meta, reads[0], reads[1]) }
    if (params.run_fastqc) {
        FASTQC(ch_short.map { meta, r1, r2 -> tuple(meta + [stage: 'raw'], [r1, r2]) })
        FASTQC_CLEAN(ch_clean.map { meta, r1, r2 -> tuple(meta + [stage: 'clean'], [r1, r2]) })
    }
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
    // Long-read BAMs carry unpaired records: samtools fastq buckets them into
    // the -0 "other" output (nf-core module naming: <prefix>_other.fastq.gz).
    SAMTOOLS_FASTQ(ch_lb.bam.map { meta, pod5, bam, lr -> tuple(meta, bam) }, false)
    ch_long_raw = ch_lb.fastq.map { meta, pod5, bam, lr -> tuple(meta, lr) }
        .mix(DORADO_BASECALL.out.long_reads, SAMTOOLS_FASTQ.out.other)

    NANOPLOT(ch_long_raw)
    FILTLONG(ch_long_raw.map { meta, fq -> tuple(meta, [], fq) })

    ch_hr = FILTLONG.out.reads.branch { meta, _fq ->
        host: meta.host_reference != null
        nohost: true
    }
    ch_host_long = ch_hr.host.map { meta, fq -> tuple(meta + [preset: 'map-ont'], fq, file(meta.host_reference)) }
    MINIMAP2_ALIGN_HOST(
        ch_host_long.map { meta, fq, _ref -> tuple(meta, fq) },
        ch_host_long.map { meta, _fq, ref -> tuple(meta, ref) },
        true,  // bam_format
        '',    // bam_index_extension
        false, // cigar_paf_format
        false  // cigar_bam
    )
    // Drop the 'preset' helper key (only needed for MINIMAP2_ALIGN_HOST's
    // ext.args) so downstream metas match the no-host-removal branch exactly.
    ch_host_bam = MINIMAP2_ALIGN_HOST.out.bam
        .map { meta, bam -> tuple(meta.findAll { entry -> entry.key != 'preset' }, bam) }
    SAMTOOLS_VIEW_HOST(
        ch_host_bam.map { meta, bam -> tuple(meta, bam, []) },
        [[], [], []], // no reference fasta
        [[], []],     // no qname file
        [[], []],     // no BED
        ''            // no index
    )
    SAMTOOLS_FASTQ_HOST(SAMTOOLS_VIEW_HOST.out.bam, true) // interleaved long reads
    ch_final_long = ch_hr.nohost.mix(SAMTOOLS_FASTQ_HOST.out.interleaved)

    // ---------------- hybrid assembly (02) ----------------
    ch_asm_in = ch_final_short.join(ch_final_long)
    if (params.hybrid_assembler == 'hybridspades') {
        HYBRIDSPADES(ch_asm_in.map { meta, r1, r2, lr -> tuple(meta, [r1, r2], [], [lr]) }, [], [])
        ch_assembly = HYBRIDSPADES.out.contigs
    } else {
        OPERA_MS(ch_asm_in)
        ch_assembly = OPERA_MS.out.assembly
    }

    QUAST(ch_assembly.map { meta, fasta -> tuple(meta, [fasta]) },
        Channel.value([[:], []]), Channel.value([[:], []]))

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
            ch_fastqc_raw = FASTQC.out.zip
            ch_fastqc_clean = FASTQC_CLEAN.out.zip
        }
        SHORT_READ_MULTIQC_INPUTS(FASTP.out.json, ch_fastqc_raw, ch_fastqc_clean, params.run_fastqc)
        MULTIQC(SHORT_READ_MULTIQC_INPUTS.out.files.map { files ->
            tuple([id: 'multiqc_illumina'], files, [], [], [], [])
        })
        // NanoPlot writes one report set per sample task; stage every HTML/TXT
        // into the MultiQC input so per-sample reports stay distinguishable.
        ch_nanoplot_qc = NANOPLOT.out.html
            .mix(NANOPLOT.out.txt)
            .map { meta, files -> files }
            .flatten()
            .collect()
        MULTIQC_ONT(ch_nanoplot_qc.map { files -> tuple([id: 'multiqc_ont'], files, [], [], [], []) })
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
        .mix(QUAST.out.tsv.map { meta, f -> f })
}
