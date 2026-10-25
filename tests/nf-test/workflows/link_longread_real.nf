// Native minimap2+samtools alignment feeding LINK_LONGREAD.
// Data: pinned nf-core/test-datasets minigut assembly and ONT reads,
// prepared by prepare_data.py (AUTOPLASM_TEST_DATA).
// The upstream minigut fixture is synthetic; first-five partition membership
// is an execution control, not independent biological plasmid/host truth.
nextflow.enable.dsl = 2

include { LINK_LONGREAD } from '../../../modules/linking/longread'

process ALIGN_FOR_LINK {
    // Test scaffolding (not a pipeline node): reproduce the real
    // contig-coverage alignment step to obtain a genuine BAM, and take the
    // first 5 real contigs as the "plasmid contigs" input (distinct file
    // name, real sequence content).
    label 'process_low'
    container 'community.wave.seqera.io/library/minimap2_samtools:b09096fc890429ce'
    publishDir "${params.outdir}/test_inputs/longread", mode: 'copy'

    input:
    tuple val(meta), path(assembly), path(reads)

    output:
    tuple val(meta), path("${meta.id}.bam"), emit: bam
    path "plasmid_contigs.fasta", emit: contigs
    path "${meta.id}.sam.gz", emit: sam

    script:
    """
    set -o pipefail
    minimap2 -ax map-ont ${assembly} ${reads} | samtools sort -o ${meta.id}.bam
    samtools view -h ${meta.id}.bam | gzip -c > ${meta.id}.sam.gz
    n=0
    while IFS= read -r line; do
        case "\$line" in
            '>'*) n=\$((n+1)) ;;
        esac
        if [ \$n -gt 5 ]; then break; fi
        printf '%s\\n' "\$line"
    done < ${assembly} > plasmid_contigs.fasta
    """
}

workflow {
    def root = params.test_data
    def assembly = file("${root}/minigut.fasta", checkIfExists: true)
    def reads = file("${root}/test_data/minigut_reads.fastq.gz", checkIfExists: true)
    ALIGN_FOR_LINK(tuple([id: 'minigut_ont'], assembly, reads))
    LINK_LONGREAD(ALIGN_FOR_LINK.out.bam
        .combine(ALIGN_FOR_LINK.out.contigs)
        .map { meta, bam, contigs -> tuple(meta, contigs, assembly, bam) })
}
