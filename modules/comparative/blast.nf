/*
 * BLASTn plasmid sequence comparison (DAG node: comparative_blast; optional
 * via params.comparative_optional_tools). Requires a BLAST database.
 */
process BLASTN {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/comparative.yml"

    publishDir "${params.outdir}/09_comparative_genomics/${meta.id}/blast", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)
    path blast_db

    output:
    tuple val(meta), path("${meta.id}.blast.tsv"), emit: results

    script:
    """
    blastn -query ${plasmid_contigs} -db ${blast_db} \\
        -out ${meta.id}.blast.tsv -outfmt 6 -num_threads ${task.cpus}
    """
}
