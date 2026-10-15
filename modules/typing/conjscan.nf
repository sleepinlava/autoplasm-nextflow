/*
 * CONJscan conjugative system detection via MacSyFinder (DAG node:
 * typing_conjscan; optional via params.typing_optional_tools).
 */
process CONJSCAN {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/macsyfinder.yml"

    publishDir "${params.outdir}/06_plasmid_typing/conjscan", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)

    output:
    tuple val(meta), path("${meta.id}.conjscan_out", type: 'dir'), emit: output_dir

    script:
    """
    macsyfinder conjscan --db-type ordered_replicon \\
        --sequence-db ${plasmid_contigs} \\
        --output-dir ${meta.id}.conjscan_out \\
        --threads ${task.cpus}
    """
}
