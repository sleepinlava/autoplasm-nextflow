process PROTEIN_INPUTS {
    cache 'deep'
    tag "${meta.id}"
    label 'process_low'
    conda "${moduleDir}/../../envs/catalogue.yml"
    container 'python:3.12-slim'

    input:
    tuple val(meta), path(genome), path(gff), path(proteins), path(cds)
    // Explicit regular files: helper changes participate in deep caching.
    path(autoplasm_helper_0, stageAs: 'prepare_prodigal_inputs.py')

    output:
    tuple val(meta), path('protein_inputs/proteins.faa'), path('protein_inputs/replicon_topology.txt'), emit: proteins
    tuple val(meta), path('protein_inputs/gene_map.tsv'), emit: gene_map
    tuple val(meta), path('protein_inputs/manifest.json'), emit: manifest
    tuple val(meta), eval("python3 -c 'import json; print(json.load(open(\"protein_inputs/manifest.json\"))[\"state\"])'"), emit: state
    tuple val("${task.process}"), val(meta), path("${meta.id}.PROTEIN_INPUTS.task_command.sh"),
          val('python3 prepare_prodigal_inputs.py -h'), eval('python3 prepare_prodigal_inputs.py -h 2>&1 | sed -n "1p"'),
          eval("sha256sum '${meta.id}.PROTEIN_INPUTS.task_command.sh'"), emit: task_provenance


    script:
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.PROTEIN_INPUTS.task_command.sh'
    python3 prepare_prodigal_inputs.py --genome "${genome}" --gff "${gff}" --proteins "${proteins}" --cds "${cds}" \\
        --output protein_inputs
    """

    stub:
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.PROTEIN_INPUTS.task_command.sh'
    mkdir protein_inputs
    touch protein_inputs/proteins.faa protein_inputs/replicon_topology.txt protein_inputs/gene_map.tsv
    echo '{"state":"stub_not_gene_prediction"}' > protein_inputs/manifest.json
    """
}
