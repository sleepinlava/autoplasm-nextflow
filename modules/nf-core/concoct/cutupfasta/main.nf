process CONCOCT_CUTUPFASTA {
    cache 'deep'
    tag "${meta.id}"
    label 'process_single'

    conda "${moduleDir}/environment.yml"
    container "${workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container
        ? 'https://depot.galaxyproject.org/singularity/concoct:1.1.0--py39h8907335_8'
        : 'quay.io/biocontainers/concoct:1.1.0--py39h8907335_8'}"

    input:
    tuple val(meta), path(fasta)
    val bed
    // Explicit regular files: helper changes participate in deep caching.
    path(autoplasm_helper_0, stageAs: 'run_concoct_cut_checked.py')

    output:
    tuple val(meta), path("*.fasta"), emit: fasta
    tuple val(meta), path("*.bed"), optional: true, emit: bed
    tuple val("${task.process}"), val('concoct'), eval('concoct --version | cut -d " " -f2'), emit: versions_concoct, topic: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    def bedfile = bed ? "-b ${prefix}.bed" : ""
    def compressed = fasta.name.toLowerCase().endsWith('.gz')
    def input_fasta = compressed ? '.concoct_input/assembly.fna' : fasta
    if ("${fasta}" == "${prefix}.fasta") {
        error("Input and output names are the same, set prefix in module configuration to disambiguate!")
    }
    """
    if ${compressed}; then
        mkdir -p .concoct_input
        gzip -cd -- ${fasta} > .concoct_input/assembly.fna
    fi

    python run_concoct_cut_checked.py \\
        ${input_fasta} \\
        ${args} \\
        ${bedfile} \\
        > ${prefix}.fasta

    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    if ("${fasta}" == "${prefix}.fasta") {
        error("Input and output names are the same, set prefix in module configuration to disambiguate!")
    }
    """
    touch ${prefix}.fasta

    """
}
