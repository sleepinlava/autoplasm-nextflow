/*
 * Plasmid circularity / terminal-overlap detection (DAG node:
 * plasmid_structure; internal handler in ABI, implemented here by
 * bin/plasmid_structure.py with the same algorithm).
 */
process PLASMID_STRUCTURE {
    tag { meta.id }
    label 'process_single'
    conda "${projectDir}/envs/python.yml"

    publishDir "${params.outdir}/04_plasmid_detection/${meta.id}", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)

    output:
    tuple val(meta), path("${meta.id}.plasmid_structure.tsv"), emit: structure

    script:
    """
    plasmid_structure.py \\
        --contigs ${plasmid_contigs} \\
        --sample-id ${meta.id} \\
        --out ${meta.id}.plasmid_structure.tsv
    """
}
