/*
 * Sequence similarity host-plasmid linking (k-mer/GC composition; DAG node:
 * host_plasmid_link_sequence; internal handler in ABI, implemented here by
 * bin/sequence_similarity_link.py). Requires MAG bins; GTDB-Tk taxonomy is
 * attached when available. Missing optional inputs arrive as empty lists.
 */
process LINK_SEQUENCE {
    tag { meta.id }
    label 'process_low'
    conda "${projectDir}/envs/python.yml"

    publishDir "${params.outdir}/07_host_prediction/linking/sequence", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs), path(mag_bins, stageAs: 'mag_bins/*'), path(host_taxonomy)

    output:
    tuple val(meta), path("${meta.id}.sequence_links.tsv"), emit: links

    script:
    def tax_arg = host_taxonomy ? "--taxonomy ${host_taxonomy}" : ''
    def bins_arg = mag_bins ? "--host-genomes mag_bins" : ''
    """
    sequence_similarity_link.py \\
        --plasmid-contigs ${plasmid_contigs} \\
        ${bins_arg} ${tax_arg} \\
        --sample-id ${meta.id} \\
        --min-similarity ${params.link_min_similarity} \\
        --out ${meta.id}.sequence_links.tsv
    """
}
