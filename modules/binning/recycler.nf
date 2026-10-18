/*
 * Recycler plasmid reconstruction from graph cycles (pipeline step:
 * plasmid_binning_recycler; optional; requires fastg graph + BAM).
 */
process RECYCLER {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/recycler.yml"
    container 'quay.io/biocontainers/recycler:0.7--py_3'

    publishDir "${params.outdir}/05_plasmid_binning/recycler", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly_graph), path(bam)

    output:
    tuple val(meta), path("${meta.id}.recycler_out", type: 'dir'), emit: output_dir

    script:
    // recycle.py requires integer -k/--max_k (the SPAdes k used to build the
    // graph); 55 is the metaSPAdes default that produces the production fastg.
    """
    recycle.py -g ${assembly_graph} -k 55 -b ${bam} \\
        -o ${meta.id}.recycler_out
    """
}
