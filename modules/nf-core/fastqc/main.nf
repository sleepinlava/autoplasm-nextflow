process FASTQC {
    tag "${meta.id}"
    label 'process_low'

    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container
?         'https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/81/816bda6dd014e810753f642611232443ddeabb2b47f9681ad43f9044816f00ff/data'
:         'community.wave.seqera.io/library/fastqc:0.13.0--b342db7b694c9af4' }"

    input:
    tuple val(meta), path(reads, stageAs: '?/*')

    output:
    tuple val(meta), path("*.html"), emit: html
    tuple val(meta), path("*.zip"), emit: zip
    tuple val("${task.process}"), val('fastqc'), eval('fastqc --version | sed "/FastQC v/!d; s/.*v//"'), emit: versions_fastqc, topic: versions
    tuple val("${task.process}"), val(meta), path("${prefix}.FASTQC.task_command.sh"),
          val('fastqc --version'), eval('fastqc --version'),
          eval("sha256sum '${prefix}.FASTQC.task_command.sh'"), emit: task_provenance

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    prefix = task.ext.prefix ?: "${meta.id}"
    // Local patch (refactor/nf-core-modules): input symlinks keep the legacy
    // alias scheme <prefix>.R1.fastq.gz / <prefix>.R2.fastq.gz (upstream uses
    // <prefix>_N.<extension>), preserving the full .fastq/.fq(+gz) suffix.
    // FastQC embeds these aliases as the report Filename, and the pipeline's
    // published layout plus regression tests assert that exact shape.
    def fastqSuffix = { input ->
        def lower = input.name.toLowerCase()
        if (lower.endsWith('.fq.gz') || lower.endsWith('.fastq.gz')) return '.fastq.gz'
        if (lower.endsWith('.fq') || lower.endsWith('.fastq')) return '.fastq'
        throw new IllegalArgumentException("FASTQC requires .fq/.fastq with optional .gz: ${input}")
    }
    // Make list of old name and new name pairs to use for renaming in the bash while loop
    def old_new_pairs = reads instanceof Path || reads.size() == 1 ? [[reads, "${prefix}${fastqSuffix.call(reads)}"]] : reads.withIndex().collect { entry, index -> [entry, "${prefix}.R${index + 1}${fastqSuffix.call(entry)}"] }
    def rename_to = old_new_pairs*.join(' ').join(' ')
    def renamed_files = old_new_pairs.collect { _old_name, new_name -> new_name }.join(' ')

    // The total amount of allocated RAM by FastQC is equal to the number of threads defined (--threads) time the amount of RAM defined (--memory)
    // https://github.com/s-andrews/FastQC/blob/1faeea0412093224d7f6a07f777fad60a5650795/fastqc#L211-L222
    // Dividing the task.memory by task.cpus allows to stick to requested amount of RAM in the label
    def memory_in_mb = task.memory
        ? (task.memory.toUnit('MB') / task.cpus).intValue()
        : null
    // FastQC memory value allowed range (100 - 10000)
    def fastqc_memory = memory_in_mb > 10000 ? 10000 : (memory_in_mb < 100 ? 100 : memory_in_mb)
    def fastqc_memory_arg = fastqc_memory ? "--memory ${fastqc_memory}" : ''

    """
    cp -- "\${BASH_SOURCE[0]}" '${prefix}.FASTQC.task_command.sh'
    printf "%s %s\\n" ${rename_to} | while read old_name new_name; do
        [ -f "\${new_name}" ] || ln -s \$old_name \$new_name
    done

    fastqc \\
        ${args} \\
        --threads ${task.cpus} \\
        ${fastqc_memory_arg} \\
        ${renamed_files}
    """

    stub:
    prefix = task.ext.prefix ?: "${meta.id}"
    """
    cp -- "\${BASH_SOURCE[0]}" '${prefix}.FASTQC.task_command.sh'
    touch ${prefix}.html
    touch ${prefix}.zip
    """
}
