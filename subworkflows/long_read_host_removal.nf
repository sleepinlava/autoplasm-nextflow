/* Long reads have neither READ1 nor READ2 SAM flags. samtools fastq -0
 * therefore owns their output even when stdout interleaving is requested.
 */
include { reportEvidence } from '../lib/report_events'
include { MINIMAP2_ALIGN as MINIMAP2_ALIGN_HOST } from '../modules/nf-core/minimap2/align/main'
include { SAMTOOLS_VIEW as SAMTOOLS_VIEW_HOST } from '../modules/nf-core/samtools/view/main'
include { SAMTOOLS_FASTQ as SAMTOOLS_FASTQ_HOST } from '../modules/nf-core/samtools/fastq/main'

workflow LONG_READ_HOST_REMOVAL {
    take:
    ch_reads // tuple(meta, fastq); meta.host_reference may be null
    preset   // map-ont or map-hifi

    main:
    ch_report_events = Channel.empty()
    ch_branches = ch_reads.branch { meta, reads ->
        host: meta.host_reference != null
        nohost: true
    }
    ch_host = ch_branches.host.map { meta, reads ->
        tuple(meta + [preset: preset], reads, file(meta.host_reference, checkIfExists: true))
    }
    MINIMAP2_ALIGN_HOST(ch_host.map { meta, reads, reference -> tuple(meta, reads) },
                        ch_host.map { meta, reads, reference -> tuple(meta, reference) },
                        true, '', false, false)
    ch_report_events = ch_report_events.mix(reportEvidence([channels: MINIMAP2_ALIGN_HOST.out], '01_qc', 'MINIMAP2_ALIGN_HOST'))
    ch_bam = MINIMAP2_ALIGN_HOST.out.bam.map { meta, bam ->
        tuple(meta.findAll { entry -> entry.key != 'preset' }, bam, [])
    }
    SAMTOOLS_VIEW_HOST(ch_bam, [[], [], []], [[], []], [[], []], '')
    ch_report_events = ch_report_events.mix(reportEvidence([channels: SAMTOOLS_VIEW_HOST.out], '01_qc', 'SAMTOOLS_VIEW_HOST'))
    SAMTOOLS_FASTQ_HOST(SAMTOOLS_VIEW_HOST.out.bam, false)
    ch_report_events = ch_report_events.mix(reportEvidence([channels: SAMTOOLS_FASTQ_HOST.out], '01_qc', 'SAMTOOLS_FASTQ_HOST'))
    ch_retained = SAMTOOLS_FASTQ_HOST.out.other.map { meta, reads ->
        def firstByte = new java.util.zip.GZIPInputStream(java.nio.file.Files.newInputStream(reads))
            .withCloseable { stream -> stream.read() }
        if (firstByte < 0) error "No non-host long reads remain for sample ${meta.id}; assembly cannot proceed"
        tuple(meta, reads)
    }

    emit:
    reads = ch_branches.nohost.mix(ch_retained)
    report_events = ch_report_events
}
