process FLYE {
    tag "$meta.id"
    label 'process_high'

    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container ?
        'https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/fa/fa1c1e961de38d24cf36c424a8f4a9920ddd07b63fdb4cfa51c9e3a593c3c979/data' :
        'community.wave.seqera.io/library/flye:2.9.5--d577924c8416ccd8' }"

    input:
    tuple val(meta), path(reads)
    val mode

    output:
    tuple val(meta), path("*.fasta.gz"), emit: fasta
    tuple val(meta), path("*.gfa.gz")  , emit: gfa
    tuple val(meta), path("*.gv.gz")   , emit: gv
    tuple val(meta), path("*.txt")     , emit: txt
    tuple val(meta), path("*.log")     , emit: log
    tuple val(meta), path("*.json")    , emit: json
    tuple val("${task.process}"), val('flye'), eval('flye --version'), emit: versions_flye, topic: versions
    tuple val("${task.process}"), val(meta), path("${prefix}.FLYE.task_command.sh"),
          val('flye --version'), eval('flye --version'),
          eval("sha256sum '${prefix}.FLYE.task_command.sh'"), emit: task_provenance

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    prefix = task.ext.prefix ?: "${meta.id}"
    def valid_mode = ["--pacbio-raw", "--pacbio-corr", "--pacbio-hifi", "--nano-raw", "--nano-corr", "--nano-hq"]
    if ( !valid_mode.contains(mode) )  { error "Unrecognised mode to run Flye. Options: ${valid_mode.join(', ')}" }
    """
    cp -- "\${BASH_SOURCE[0]}" '${prefix}.FLYE.task_command.sh'
    flye \\
        $mode \\
        $reads \\
        --out-dir . \\
        --threads \\
        $task.cpus \\
        $args

    gzip -c assembly.fasta > ${prefix}.assembly.fasta.gz
    gzip -c assembly_graph.gfa > ${prefix}.assembly_graph.gfa.gz
    gzip -c assembly_graph.gv > ${prefix}.assembly_graph.gv.gz
    mv assembly_info.txt ${prefix}.assembly_info.txt
    mv flye.log ${prefix}.flye.log
    mv params.json ${prefix}.params.json
    """

    stub:
    prefix = task.ext.prefix ?: "${meta.id}"
    """
    cp -- "\${BASH_SOURCE[0]}" '${prefix}.FLYE.task_command.sh'
    echo stub | gzip -c > ${prefix}.assembly.fasta.gz
    echo stub | gzip -c > ${prefix}.assembly_graph.gfa.gz
    echo stub | gzip -c > ${prefix}.assembly_graph.gv.gz
    echo contig_1 > ${prefix}.assembly_info.txt
    echo stub > ${prefix}.flye.log
    echo stub > ${prefix}.params.json
    """
}
