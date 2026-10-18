/*
 * Prepare the non-redundant plasmid catalog input (pipeline step:
 * plasmid_catalog_prepare, implemented by bin/plasmid_catalog_prepare.R).
 * The input FASTA files are explicit path
 * dependencies from the consensus channel; published output directories are
 * not used as workflow inputs.
 */
process PLASMID_CATALOG_PREPARE {
    tag 'catalog_prepare'
    label 'process_single'
    conda "${projectDir}/envs/r_analysis.yml"
    // R 包集合以 envs/r_analysis.yml 为准；镜像需提供 data.table/vegan/Biostrings/Rsamtools
    container 'autoplasm-r-analysis:latest'

    publishDir "${params.outdir}/09_comparative_genomics", mode: params.publish_dir_mode

    input:
    path contigs

    output:
    path "plasmid_catalog_input.fasta", emit: combined

    script:
    def files = (contigs in List ? contigs : [contigs])
    if (files.isEmpty()) {
        throw new IllegalArgumentException('PLASMID_CATALOG_PREPARE requires at least one FASTA')
    }
    def shellQuote = { value -> "'" + value.toString().replace("'", "'\"'\"'") + "'" }
    def contigArgs = files.collect { shellQuote.call(it) }.join(' ')
    """
    plasmid_catalog_prepare.R \\
        --contigs ${contigArgs} \\
        --out plasmid_catalog_input.fasta
    """
}
