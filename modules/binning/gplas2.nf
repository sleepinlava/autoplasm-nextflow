/*
 * gplas2 graph-based plasmid binning (pipeline step: plasmid_binning_gplas2;
 * fixed official source; requires same-run SPAdes GFA + node predictions).
 */
process GPLAS2 {
    cache 'deep'
    tag { meta.gplas_original_meta.id }
    label 'process_medium'
    conda "${moduleDir}/../../envs/gplas2.yml"

    publishDir "${params.outdir}/05_plasmid_binning/gplas2", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly_graph), path(node_predictions), path(ready_marker)
    tuple path(source, stageAs: 'sources/gplas'), val(source_identity)
    // Explicit regular files: helper changes participate in deep caching.
    path(autoplasm_helper_0, stageAs: '.gplas_checked.py')


    output:
    tuple val(meta), path("${meta.gplas_original_meta.id}.gplas2"), emit: bins
    tuple val(meta), path("${meta.gplas_original_meta.id}.gplas_runtime.json"), emit: runtime

    script:
    def originalId = meta.gplas_original_meta.id
    """
    python3 .gplas_checked.py --source '${source}' --graph '${assembly_graph}' \\
        --predictions '${node_predictions}' --name '${originalId}' \\
        --record '${originalId}.gplas_runtime.json'
    mkdir '${originalId}.gplas2'
    cp 'results/${originalId}_results.tab' 'results/${originalId}_bins.tab' '${originalId}.gplas2/'
    cp results/${originalId}_bin_*.fasta '${originalId}.gplas2/'
    if [ -f 'results/${originalId}_chromosome_repeats.tab' ]; then
        cp 'results/${originalId}_chromosome_repeats.tab' '${originalId}.gplas2/'
    fi
    if [ -f 'results/${originalId}_plasmidome_network.png' ]; then
        cp 'results/${originalId}_plasmidome_network.png' '${originalId}.gplas2/'
    fi
    """
}
