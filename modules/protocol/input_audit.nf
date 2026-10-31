process PROTOCOL_INPUT_AUDIT {
    tag { meta.id }
    label 'process_single'
    conda "${projectDir}/envs/seqkit.yml"
    cache 'deep'
    input:
    tuple val(meta), path(read1), path(read2)
    path code_assets,stageAs:'source_assets/*'
    output:
    path("*.task_command.sh"), emit: commands
    tuple val(meta), path("${meta.id}.input_audit"), emit: audit
    script:
    """
    cp -- "\${BASH_SOURCE[0]}" "${meta.id}.${task.process.tokenize(':').last()}.task_command.sh"
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    export PYTHONPATH=\$PWD/analysis_code
    python3 analysis_code/protocol_input_audit.py audit --sample '${meta.id}' --reads '${read1}' '${read2}' --output '${meta.id}.input_audit'
    seqkit stats --all --tabular '${read1}' '${read2}' > '${meta.id}.input_audit/seqkit_stats.tsv'
    seqkit version > '${meta.id}.input_audit/version.txt'
    """
}
process PROTOCOL_RETENTION {
    tag { meta.id }
    label 'process_single'
    conda "${projectDir}/envs/seqkit.yml"
    publishDir "${params.outdir}/01_qc/retention", mode: params.publish_dir_mode
    cache 'deep'
    input:
    tuple val(meta), path(fastp_json), path(read1), path(read2)
    path code_assets,stageAs:'source_assets/*'
    output:
    path("*.task_command.sh"), emit: commands
    tuple val(meta), path("${meta.id}.retention.tsv"), emit: retention
    script:
    """
    cp -- "\${BASH_SOURCE[0]}" "${meta.id}.${task.process.tokenize(':').last()}.task_command.sh"
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    export PYTHONPATH=\$PWD/analysis_code
    python3 analysis_code/protocol_input_audit.py retention --sample '${meta.id}' --fastp '${fastp_json}' \\
      --reads '${read1}' '${read2}' --output '${meta.id}.retention.tsv'
    """
}
process PROTOCOL_HOST_FILTER {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/modules/nf-core/samtools/fastq/environment.yml"
    container 'community.wave.seqera.io/library/htslib_samtools:1.24--d697cfb9dce007cd'
    publishDir "${params.outdir}/01_qc/host_removal/paired", mode: params.publish_dir_mode
    input:
    tuple val(meta), path(bam), path(reference)
    output:
    path("*.task_command.sh"), emit: commands
    tuple val(meta), path("${meta.id}.hostfree_1.fastq.gz"), path("${meta.id}.hostfree_2.fastq.gz"), emit: reads
    tuple val(meta), path("${meta.id}.host_filter.json"), emit: statistics
    tuple val(meta), path("${meta.id}.host_reference.sha256"), emit: reference_identity
    script:
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.PROTOCOL_HOST_FILTER.task_command.sh'
    samtools sort -n -@ ${task.cpus} -o names.bam '${bam}'
    samtools fastq -@ ${task.cpus} -f 12 -F 2304 -n \\
      -1 '${meta.id}.hostfree_1.fastq.gz' -2 '${meta.id}.hostfree_2.fastq.gz' -0 /dev/null -s /dev/null names.bam
    samtools flagstat -O json '${bam}' > '${meta.id}.host_filter.json'
    sha256sum '${reference}' > '${meta.id}.host_reference.sha256'
    """
}
