/*
 * MacSyFinder macromolecular system detection (DAG node: typing_macsyfinder;
 * optional via params.typing_optional_tools).
 */
process MACSYFINDER {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/macsyfinder.yml"

    publishDir "${params.outdir}/06_plasmid_typing/macsyfinder", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)

    output:
    tuple val(meta), path("${meta.id}.macsyfinder_out", type: 'dir'), emit: output_dir

    script:
    """
    macsyfinder --sequence-db ${plasmid_contigs} --db-type ordered_replicon \\
        --output-dir ${meta.id}.macsyfinder_out --threads ${task.cpus}
    """
}
