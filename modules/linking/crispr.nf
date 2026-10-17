/*
 * CRISPR spacer matching is not implemented yet. Keep the process boundary so
 * direct callers receive an explicit failure instead of a fabricated result.
 */
process LINK_CRISPR {
    tag "${meta.id}"
    label 'process_medium'
    conda "${projectDir}/envs/minced.yml"
    container 'quay.io/biocontainers/minced:0.4.2--hdfd78af_1'

    publishDir "${params.outdir}/07_host_prediction/linking/crispr", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs), path(host_genomes)

    output:
    tuple val(meta), path("${meta.id}.crispr_links.tsv"), emit: links
    tuple val(meta), path("${meta.id}.crispr_spacers.fa"), emit: spacers

    script:
    """
    echo "ERROR: CRISPR host-plasmid linking is not implemented; disable crispr" >&2
    exit 2
    """
}
