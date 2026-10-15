/*
 * COPLA PTU classification (DAG node: typing_copla; optional via
 * params.typing_optional_tools). Requires the COPLA reference graph/list.
 */
process COPLA {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/copla.yml"

    publishDir "${params.outdir}/06_plasmid_typing/copla", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)
    path copla_refgraph
    path copla_reflist

    output:
    tuple val(meta), path("${meta.id}.copla.tsv"), emit: typing

    script:
    """
    copla --input ${plasmid_contigs} --refgraph ${copla_refgraph} \\
        --reflist ${copla_reflist} --output-dir copla_out
    find copla_out -name '*.tsv' | head -1 | xargs -I{} cp {} ${meta.id}.copla.tsv
    """
}
