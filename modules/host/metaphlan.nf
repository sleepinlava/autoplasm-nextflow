/*
 * MetaPhlAn4 taxonomic profiling (DAG node: host_prediction_metaphlan;
 * default host profiler on read-based platforms). Requires the MetaPhlAn
 * database. Handles both short paired-end and long reads.
 */
process METAPHLAN {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/host_prediction.yml"

    publishDir "${params.outdir}/07_host_prediction/${meta.id}", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(reads)
    path metaphlan_db

    output:
    tuple val(meta), path("${meta.id}.metaphlan.tsv"), emit: profile

    script:
    def input_arg = reads instanceof List ? reads.collect { it.toString() }.join(',') : reads.toString()
    """
    metaphlan ${input_arg} --input_type fastq \\
        --nproc ${task.cpus} \\
        --db_dir ${metaphlan_db} \\
        -o ${meta.id}.metaphlan.tsv \\
        --mapout ${meta.id}.map.bowtie2out.txt
    """
}
