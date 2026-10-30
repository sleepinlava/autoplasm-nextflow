/*
 * Local BAM indexing bridge for the MAG subworkflow (pipeline step:
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
    container 'community.wave.seqera.io/library/htslib_samtools:1.24--d697cfb9dce007cd'

    input:
    tuple val(meta), path(bam)

    output:
    tuple val(meta), path("${bam}.bai"), emit: bai
    tuple val("${task.process}"), val(meta), path("${meta.id}.SAMTOOLS_INDEX.task_command.sh"),
          val('samtools --version'), eval('samtools --version | sed -n "1p"'),
          eval("sha256sum '${meta.id}.SAMTOOLS_INDEX.task_command.sh'"), emit: task_provenance


    script:
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.SAMTOOLS_INDEX.task_command.sh'
    samtools index -@ ${task.cpus} ${bam}
    """
}
