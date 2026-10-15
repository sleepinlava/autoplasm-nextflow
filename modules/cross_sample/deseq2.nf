/*
 * DESeq2 differential plasmid abundance (DAG node:
 * multisample_differential_deseq2). Uses the ABI R script verbatim.
 */
process DESEQ2 {
    tag 'deseq2'
    label 'process_medium'
    conda "${projectDir}/envs/deseq2.yml"

    publishDir "${params.outdir}/11_diversity", mode: params.publish_dir_mode

    input:
    path abundance_table
    path sample_metadata

    output:
    path "differential_plasmids.tsv", emit: results

    script:
    """
    Rscript ${projectDir}/bin/deseq2_plasmid.R \\
        --abundance ${abundance_table} \\
        --metadata ${sample_metadata} \\
        --output differential_plasmids.tsv
    """
}
