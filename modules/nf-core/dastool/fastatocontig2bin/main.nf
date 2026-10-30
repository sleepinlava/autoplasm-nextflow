process DASTOOL_FASTATOCONTIG2BIN {
    tag "${meta.id}"
    label 'process_single'

    conda "${moduleDir}/environment.yml"
    container "${workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container
        ? 'https://depot.galaxyproject.org/singularity/das_tool:1.1.7--r44hdfd78af_1'
        : 'quay.io/biocontainers/das_tool:1.1.7--r44hdfd78af_1'}"

    input:
    tuple val(meta), path(fasta)
    val extension

    output:
    tuple val(meta), path("*.tsv"), emit: fastatocontig2bin
    tuple val("${task.process}"), val('dastool'), eval('DAS_Tool --version 2>&1 | grep "DAS Tool" | sed "s/DAS Tool //"'), topic: versions, emit: versions_dastool
    tuple val("${task.process}"), val(meta), path("${meta.id}.DASTOOL_FASTATOCONTIG2BIN.task_command.sh"),
          val('DAS_Tool --version'), eval('DAS_Tool --version 2>&1 | sed -n "1p"'),
          eval("sha256sum '${meta.id}.DASTOOL_FASTATOCONTIG2BIN.task_command.sh'"), emit: task_provenance


    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    def file_extension = extension ? extension : "fasta"
    // Local patch (refactor/nf-core-modules): upstream only decompresses a
    // single input; our callers stage a list of gzipped bin fastas here.
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.DASTOOL_FASTATOCONTIG2BIN.task_command.sh'
    find . -maxdepth 1 -name '*.gz' -exec gunzip -q -f {} +

    Fasta_to_Contig2Bin.sh \\
        ${args} \\
        -i . \\
        -e ${file_extension} \\
        > ${prefix}.tsv
    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.DASTOOL_FASTATOCONTIG2BIN.task_command.sh'
    """
}
