process CONCOCT_MERGECUTUPCLUSTERING {
    tag "${meta.id}"
    label 'process_single'

    conda "${moduleDir}/environment.yml"
    container "${workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container
        ? 'https://depot.galaxyproject.org/singularity/concoct:1.1.0--py39h8907335_8'
        : 'quay.io/biocontainers/concoct:1.1.0--py39h8907335_8'}"

    input:
    tuple val(meta), path(clustering_csv)

    output:
    tuple val(meta), path("*.csv"), emit: csv
    tuple val("${task.process}"), val('concoct'), eval('concoct --version | cut -d " " -f2'), emit: versions_concoct, topic: versions
    tuple val("${task.process}"), val(meta), path("${meta.id}.CONCOCT_MERGECUTUPCLUSTERING.task_command.sh"),
          val('concoct --version'), eval('concoct --version'),
          eval("sha256sum '${meta.id}.CONCOCT_MERGECUTUPCLUSTERING.task_command.sh'"), emit: task_provenance


    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    if ("${clustering_csv}" == "${prefix}.csv") {
        error("Input and output names are the same, set prefix in module configuration to disambiguate!")
    }
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.CONCOCT_MERGECUTUPCLUSTERING.task_command.sh'
    merge_cutup_clustering.py \\
        ${args} \\
        ${clustering_csv} \\
        > ${prefix}.csv

    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    if ("${clustering_csv}" == "${prefix}.csv") {
        error("Input and output names are the same, set prefix in module configuration to disambiguate!")
    }
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.CONCOCT_MERGECUTUPCLUSTERING.task_command.sh'
    touch ${prefix}.csv

    """
}
