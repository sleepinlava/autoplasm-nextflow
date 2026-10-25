/*
 * Recycler plasmid reconstruction from graph cycles (pipeline step:
 * plasmid_binning_recycler; optional; requires same-graph BAM/BAI and k provenance).
 */
process RECYCLER {
    cache 'deep'
    tag { meta.id }
    label 'process_medium'
    conda "${moduleDir}/../../envs/recycler.yml"
    container 'quay.io/biocontainers/recycler:0.7--py_3'

    publishDir "${params.outdir}/05_plasmid_binning/recycler", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly_graph), path(provenance), path(bam), path(bai)
    // Explicit regular files: helper changes participate in deep caching.
    tuple path(autoplasm_helper_0, stageAs: 'validate_recycler_inputs.py'), path(autoplasm_helper_1, stageAs: 'run_recycler_checked.py')

    output:
    tuple val(meta), path("${meta.id}.recycler_out", type: 'dir'), emit: output_dir

    script:
    """
    python validate_recycler_inputs.py --graph "${assembly_graph}" --bam "${bam}" \\
        --provenance "${provenance}" --out ${meta.id}.recycler.inputs.json
    python run_recycler_checked.py --graph "${assembly_graph}" --bam "${bam}" \\
        --contract ${meta.id}.recycler.inputs.json --out ${meta.id}.recycler_out
    cp ${meta.id}.recycler.inputs.json ${meta.id}.recycler_out/input_contract.json
    cp "${provenance}" ${meta.id}.recycler_out/graph_provenance.json
    """
}
