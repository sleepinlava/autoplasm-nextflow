/* GFA segments are classified independently of assembled-contig calls. */
process GPLAS2_NODES {
    cache 'deep'
    tag { meta.gplas_original_meta.id }
    label 'process_low'
    conda "${moduleDir}/../../envs/catalogue.yml"
    publishDir "${params.outdir}/05_plasmid_binning/gplas2/nodes", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(graph)
    // Explicit regular files: helper changes participate in deep caching.
    path(autoplasm_helper_0, stageAs: '.gplas_inputs.py')


    output:
    tuple val(meta), path("${meta.id}.gplas.gfa"), path("${meta.id}.gplas_nodes.fasta"), emit: nodes
    tuple val(meta), path("${meta.id}.gplas_nodes.json"), emit: state
    tuple val("${task.process}"), val(meta), path("${meta.id}.GPLAS2_NODES.task_command.sh"),
          val('python3 .gplas_inputs.py --help'), eval('python3 .gplas_inputs.py --help 2>&1 | sed -n "1p"'),
          eval("sha256sum '${meta.id}.GPLAS2_NODES.task_command.sh'"), emit: task_provenance


    script:
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.GPLAS2_NODES.task_command.sh'
    python3 .gplas_inputs.py prepare --graph '${graph}' --prefix '${meta.id}' \\
        --sample-id '${meta.gplas_original_meta.id}'
    """
}

process GPLAS2_PREDICTIONS {
    cache 'deep'
    tag { meta.gplas_original_meta.id }
    label 'process_low'
    conda "${moduleDir}/../../envs/catalogue.yml"
    publishDir "${params.outdir}/05_plasmid_binning/gplas2/predictions", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(graph), path(consensus), path(assessment)
    // Explicit regular files: helper changes participate in deep caching.
    path(autoplasm_helper_0, stageAs: '.gplas_inputs.py')


    output:
    tuple val(meta), path(graph), path("${meta.id}.gplas_prediction.tab"), path("${meta.id}.gplas_prediction.tab.ready"), optional: true, emit: ready
    tuple val(meta), path("${meta.id}.gplas_prediction.tab"), emit: predictions
    tuple val(meta), path("${meta.id}.gplas_prediction.state.json"), emit: state
    tuple val("${task.process}"), val(meta), path("${meta.id}.GPLAS2_PREDICTIONS.task_command.sh"),
          val('python3 .gplas_inputs.py --help'), eval('python3 .gplas_inputs.py --help 2>&1 | sed -n "1p"'),
          eval("sha256sum '${meta.id}.GPLAS2_PREDICTIONS.task_command.sh'"), emit: task_provenance


    script:
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.GPLAS2_PREDICTIONS.task_command.sh'
    python3 .gplas_inputs.py predictions --graph '${graph}' --consensus '${consensus}' \\
        --genomad-assessment '${assessment}' \\
        --output '${meta.id}.gplas_prediction.tab' --sample-id '${meta.gplas_original_meta.id}' \\
        --classified-sample-id '${meta.id}'
    """
}
