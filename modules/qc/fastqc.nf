/*
 * FastQC on raw or cleaned short reads (DAG nodes: qc_fastqc_raw / qc_fastqc_clean;
 * optional, enabled by params.run_fastqc).
 */
process FASTQC {
    tag { "${meta.id}.${stage}" }
    label 'process_low'
    conda "${projectDir}/envs/qc_short.yml"

    publishDir "${params.outdir}/01_qc/fastqc", mode: params.publish_dir_mode

    input:
    tuple val(meta), val(stage), path(read1, stageAs: 'read1/*'), path(read2, stageAs: 'read2/*')

    output:
    tuple val(meta), path("${meta.id}.${stage}.R*_fastqc.zip"),
        path("${meta.id}.${stage}.R*_fastqc.html"), emit: results

    script:
    if (!(stage in ['raw', 'clean'])) {
        throw new IllegalArgumentException("FASTQC stage must be raw or clean, got ${stage}")
    }
    def shellQuote = { value -> "'" + value.toString().replace("'", "'\"'\"'") + "'" }
    def fastqSuffix = { input ->
        def lower = input.name.toLowerCase()
        if (lower.endsWith('.fq.gz') || lower.endsWith('.fastq.gz')) return '.fastq.gz'
        if (lower.endsWith('.fq') || lower.endsWith('.fastq')) return '.fastq'
        throw new IllegalArgumentException("FASTQC requires .fq/.fastq with optional .gz: ${input}")
    }
    def alias1 = "${meta.id}.${stage}.R1${fastqSuffix(read1)}"
    def alias2 = "${meta.id}.${stage}.R2${fastqSuffix(read2)}"
    """
    ln -s -- ${shellQuote(read1)} ${shellQuote(alias1)}
    ln -s -- ${shellQuote(read2)} ${shellQuote(alias2)}
    fastqc --threads ${task.cpus} --extract --outdir . ${shellQuote(alias1)} ${shellQuote(alias2)}
    """
}
