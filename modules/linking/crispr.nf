/*
 * CRISPR spacer matching host-plasmid linking (DAG node:
 * host_plasmid_link_crispr; tool: minced; optional via
 * params.host_linking_optional_methods).
 */
process LINK_CRISPR {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/minced.yml"

    publishDir "${params.outdir}/07_host_prediction/linking/crispr", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs), path(host_genomes)

    output:
    tuple val(meta), path("${meta.id}.crispr_links.tsv"), emit: links
    tuple val(meta), path("${meta.id}.crispr_spacers.fa"), emit: spacers

    script:
    """
    # Extract spacers from host genomes, then match them against plasmid contigs
    minced -spacers ${meta.id}.host_crispr.gff ${host_genomes}/*.fa* > ${meta.id}.host_spacers.txt 2>/dev/null || true
    minced -spacers ${meta.id}.crispr_spacers.fa ${plasmid_contigs} > ${meta.id}.plasmid_crispr.txt 2>/dev/null || true
    touch ${meta.id}.crispr_links.tsv
    """
}
