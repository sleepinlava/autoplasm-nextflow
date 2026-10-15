/*
 * MMseqs2 cross-sample plasmid catalog clustering (DAG node:
 * comparative_mmseqs2; default comparative tool).
 */
process MMSEQS2 {
    tag 'mmseqs2'
    label 'process_medium'
    conda "${projectDir}/envs/comparative.yml"

    publishDir "${params.outdir}/09_comparative_genomics", mode: params.publish_dir_mode

    input:
    path combined_plasmids

    output:
    path "plasmid_catalog_cluster.tsv", emit: clusters
    path "plasmid_catalog_rep_seq.fasta", emit: representatives

    script:
    """
    mmseqs easy-cluster ${combined_plasmids} plasmid_catalog tmp \\
        --min-seq-id ${params.mmseqs2_min_seq_id} -c ${params.mmseqs2_min_cov} \\
        --cov-mode 1 --threads ${task.cpus}
    """
}
