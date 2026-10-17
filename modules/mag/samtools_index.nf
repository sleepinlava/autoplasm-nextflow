/*
 * Local BAM indexing bridge for the MAG subworkflow (DAG node:
 * mag_samtools_index). The nf-core bam-consuming binning modules
 * (METABAT2_JGISUMMARIZEBAMCONTIGDEPTHS, CONCOCT_CONCOCTCOVERAGETABLE)
 * require a BAI next to the BAM, but the contig coverage subworkflow
 * emits bam without an index. No nf-core samtools/index module is
 * vendored, so this minimal bridge runs samtools index only.
 */
process SAMTOOLS_INDEX {
    tag { meta.id }
    label 'process_low'
    conda "${projectDir}/envs/abundance.yml"

    input:
    tuple val(meta), path(bam)

    output:
    tuple val(meta), path("${bam}.bai"), emit: bai

    script:
    """
    samtools index -@ ${task.cpus} ${bam}
    """
}
