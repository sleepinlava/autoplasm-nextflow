/*
 * gplas2 graph-based plasmid binning (DAG node: plasmid_binning_gplas2;
 * optional; requires an assembly graph from metaFlye/hifiasm).
 */
process GPLAS2 {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/gplas2.yml"

    publishDir "${params.outdir}/05_plasmid_binning/gplas2", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs), path(assembly_graph)

    output:
    tuple val(meta), path("${meta.id}.gplas2.tsv"), emit: bins

    script:
    """
    # gplas2 classifies graph nodes; plasmid_contigs act as the prediction input
    gplas2 --input ${assembly_graph} --classifier predict \\
        --prediction ${plasmid_contigs} --name ${meta.id}
    mv ${meta.id}*results*.tsv ${meta.id}.gplas2.tsv 2>/dev/null || \\
        find . -name '*.tsv' -maxdepth 2 | head -1 | xargs -I{} mv {} ${meta.id}.gplas2.tsv
    """
}
