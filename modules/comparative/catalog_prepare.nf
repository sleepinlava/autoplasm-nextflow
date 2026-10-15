/*
 * Prepare the non-redundant plasmid catalog input (DAG node:
 * plasmid_catalog_prepare; internal handler in ABI, implemented here by
 * bin/plasmid_catalog_prepare.py). Like the ABI handler, it globs the
 * published 04_plasmid_detection directory (this avoids staging collisions
 * of the per-sample plasmid_contigs.fasta files). The `trigger` input
 * carries one item per finished sample so all consensus steps are complete
 * before the glob runs.
 */
process PLASMID_CATALOG_PREPARE {
    tag 'catalog_prepare'
    label 'process_single'
    conda "${projectDir}/envs/python.yml"

    publishDir "${params.outdir}/09_comparative_genomics", mode: params.publish_dir_mode

    input:
    val trigger

    output:
    path "plasmid_catalog_input.fasta", emit: combined

    script:
    """
    plasmid_catalog_prepare.py \\
        --contigs ${params.outdir}/04_plasmid_detection/consensus/*.plasmid_contigs.fasta \\
        --out plasmid_catalog_input.fasta
    """
}
