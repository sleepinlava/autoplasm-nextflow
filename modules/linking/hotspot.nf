/*
 * HOTSPOT Transformer host prediction (optional host-linking
 * module; Ji et al. 2023, Bioinformatics 39(5):btad283;
 * https://github.com/Orin-beep/HOTSPOT). HOTSPOT is not packaged for
 * bioconda, so this module expects a cloned HOTSPOT repository
 * (--hotspot_home) plus the downloaded database/ and models/ folders
 * (--hotspot_db / --hotspot_models; see the HOTSPOT README's prepare_db.sh
 * and prepare_mdl.sh). host_lineage.tsv is converted to the host-link schema;
 * host_id is the deepest predicted taxonomic level (species -> phylum).
 */
process LINK_HOTSPOT {
    tag "${meta.id}"
    label 'process_medium'
    cache 'deep'
    conda "${moduleDir}/../../envs/hotspot-linux-64.lock"

    publishDir "${params.outdir}/07_host_prediction/linking/hotspot", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs, stageAs: 'plasmid_input.fasta')
    path hotspot_program, stageAs: 'hotspot_program/*'
    path hotspot_database, stageAs: 'hotspot_database/*'
    tuple path(hotspot_models, stageAs: 'hotspot_models'), path(hotspot_model_dependencies, stageAs: 'hotspot_model_dependencies/*')
    // Explicit regular files: helper changes participate in deep caching.
    tuple path(autoplasm_helper_0, stageAs: 'convert_hotspot_lineage.py'), path(autoplasm_helper_1, stageAs: 'hotspot_runtime.py')

    output:
    tuple val(meta), path("${meta.id}.hotspot_links.tsv"), emit: links
    tuple val(meta), path("${meta.id}.host_lineage.tsv"), emit: lineage
    tuple val(meta), path("${meta.id}.hotspot_conversion.json"), emit: conversion
    tuple val(meta), path("${meta.id}.hotspot_runtime.json"), emit: runtime

    script:
    """
    python3 hotspot_runtime.py --source-dir hotspot_program --database hotspot_database --models hotspot_models \\
        --fasta "${plasmid_contigs}" --threads ${task.cpus} \\
        --runtime-record "${meta.id}.hotspot_runtime.json"
    python3 convert_hotspot_lineage.py --lineage hotspot_results/host_lineage.tsv --sample-id "${meta.id}" \\
        --fasta "${plasmid_contigs}" --output "${meta.id}.hotspot_links.tsv" \\
        --manifest "${meta.id}.hotspot_conversion.json"
    cp hotspot_results/host_lineage.tsv ${meta.id}.host_lineage.tsv
    """
}
