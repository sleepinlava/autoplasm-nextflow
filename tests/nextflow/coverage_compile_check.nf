include { BOWTIE2_ALIGN } from '../../modules/nf-core/bowtie2/align/main'
include { COVERM_CONTIG } from '../../modules/nf-core/coverm/contig/main'
include { SAMTOOLS_FASTQ } from '../../modules/nf-core/samtools/fastq/main'
include { SAMTOOLS_MERGE } from '../../modules/nf-core/samtools/merge/main'
include { SAMTOOLS_SORT } from '../../modules/nf-core/samtools/sort/main'
include { SAMTOOLS_VIEW } from '../../modules/nf-core/samtools/view/main'
include { MINIMAP2_ALIGN } from '../../modules/nf-core/minimap2/align/main'
workflow { println 'compiled' }
