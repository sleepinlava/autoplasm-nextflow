/*
 * Recycler plasmid reconstruction from graph cycles (DAG node:
 * plasmid_binning_recycler; optional; requires fastg graph + BAM).
 */
process RECYCLER {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/recycler.yml"

    publishDir "${params.outdir}/05_plasmid_binning/recycler", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly_graph), path(plasmid_contigs), path(bam)

    output:
    tuple val(meta), path("${meta.id}.recycler_out", type: 'dir'), emit: output_dir

    script:
    """
    recycle.py -g ${assembly_graph} -k ${plasmid_contigs} -b ${bam} \\
        -o ${meta.id}.recycler_out
    """
}
