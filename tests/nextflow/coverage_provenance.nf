include { BOWTIE2_ALIGN } from '../../modules/nf-core/bowtie2/align/main'
include { COVERM_CONTIG } from '../../modules/nf-core/coverm/contig/main'
workflow {
    idx_dir = file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261029-coverage-provenance/index')
    reads = Channel.of(tuple([id: 'cov-iface', single_end: false],
        [file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261027-ena-multi/ena/SRR19638267_1.fastq.gz'),
         file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261027-ena-multi/ena/SRR19638267_2.fastq.gz')]))
    BOWTIE2_ALIGN(reads, Channel.of(tuple([:], idx_dir)),
                  Channel.of(tuple([:], file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261020-quast-real/pUTI89.fasta'))), false, true)
    BOWTIE2_ALIGN.out.task_provenance.view { it -> "PROV ${it[0]} sha=${it[5]}" }
    COVERM_CONTIG(BOWTIE2_ALIGN.out.bam, Channel.of(tuple([:], file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261020-quast-real/pUTI89.fasta'))), true, false, false)
    COVERM_CONTIG.out.task_provenance.view { it -> "PROV ${it[0]} sha=${it[5]}" }
}
