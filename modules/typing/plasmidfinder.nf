/*
 * PlasmidFinder replicon/Inc typing (DAG node: typing_plasmidfinder; default
 * enabled). Requires the PlasmidFinder database.
 */
process PLASMIDFINDER {
    tag { meta.id }
    label 'process_low'
    conda "${projectDir}/envs/typing.yml"

    publishDir "${params.outdir}/06_plasmid_typing/plasmidfinder", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)
    path plasmidfinder_db

    output:
    tuple val(meta), path("${meta.id}.plasmidfinder.tsv"), emit: typing
    tuple val(meta), path("${meta.id}.plasmidfinder_out", type: 'dir'), emit: output_dir

    script:
    """
    python -m plasmidfinder -i ${plasmid_contigs} -o ${meta.id}.plasmidfinder_out \\
        -p ${plasmidfinder_db} --legacy -x
    if [ -f ${meta.id}.plasmidfinder_out/results_tab.tsv ]; then
        cp ${meta.id}.plasmidfinder_out/results_tab.tsv ${meta.id}.plasmidfinder.tsv
    else
        find ${meta.id}.plasmidfinder_out -name '*tab*' | head -1 | xargs -I{} cp {} ${meta.id}.plasmidfinder.tsv
    fi
    """
}
