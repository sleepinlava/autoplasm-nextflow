/*
 * ONT platform subworkflow (DAG platform_resolution.ont):
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
include { MINIMAP2_ALIGN as MINIMAP2_ALIGN_HOST } from '../modules/nf-core/minimap2/align/main'
include { SAMTOOLS_VIEW as SAMTOOLS_VIEW_HOST } from '../modules/nf-core/samtools/view/main'
include { SAMTOOLS_FASTQ as SAMTOOLS_FASTQ_HOST } from '../modules/nf-core/samtools/fastq/main'
include { FLYE as METAFLYE } from '../modules/nf-core/flye/main'
include { MEDAKA } from '../modules/nf-core/medaka/main'
include { QUAST } from '../modules/nf-core/quast/main'
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
    // Long-read BAMs carry unpaired records: samtools fastq buckets them into
    // the -0 "other" output (nf-core module naming: <prefix>_other.fastq.gz).
    SAMTOOLS_FASTQ(ch_br.bam.map { meta, pod5, bam, lr -> tuple(meta, bam) }, false)
    ch_long_raw = ch_br.fastq.map { meta, pod5, bam, lr -> tuple(meta, lr) }
        .mix(DORADO_BASECALL.out.long_reads, SAMTOOLS_FASTQ.out.other)

    // ---------------- QC (01) ----------------
    NANOPLOT(ch_long_raw)
    FILTLONG(ch_long_raw.map { meta, fq -> tuple(meta, [], fq) })

    // ---------------- host removal (optional) ----------------
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

    // ---------------- assembly (02) + optional medaka polishing ----------------
    METAFLYE(ch_final_long, '--nano-raw')
    ch_assembly = METAFLYE.out.fasta
    if (params.polishing_tools.contains('medaka')) {
        // nf-core medaka takes (meta, reads, assembly) — note the order.
        MEDAKA(ch_final_long.join(METAFLYE.out.fasta))
        ch_assembly = MEDAKA.out.assembly
    }

    QUAST(ch_assembly.map { meta, fasta -> tuple(meta, [fasta]) },
        Channel.value([[:], []]), Channel.value([[:], []]))

    // ---------------- contig coverage ----------------
    CONTIG_COVERAGE(ch_assembly, Channel.empty(), ch_final_long, 'map-ont')

    // ---------------- plasmid detection (04) ----------------
    PLASMID_DETECTION(ch_assembly, Channel.empty())
    ch_plasmids = PLASMID_DETECTION.out.plasmid_contigs.filter { meta, f -> f.size() > 0 }

    PLASMID_DOWNSTREAM(
        ch_plasmids, METAFLYE.out.gfa, CONTIG_COVERAGE.out.bam,
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
        // NanoPlot writes one report set per sample task; stage every HTML/TXT
        // into the MultiQC input so per-sample reports stay distinguishable.
        ch_nanoplot_qc = NANOPLOT.out.html
            .mix(NANOPLOT.out.txt)
            .map { meta, files -> files }
            .flatten()
            .collect()
        MULTIQC(ch_nanoplot_qc.map { files -> tuple([id: 'multiqc_ont'], files, [], [], [], []) })
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
        .mix(QUAST.out.tsv.map { meta, f -> f })
}
