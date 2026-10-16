/*
 * Sequence similarity host-plasmid linking (k-mer/GC composition; DAG node:
 * host_plasmid_link_sequence; internal handler in ABI, implemented here by
 * bin/sequence_similarity_link.py). Reads the actual staged MAG directory;
 * GTDB-Tk taxonomy is attached when available. Missing optional inputs arrive
 * as empty lists.
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
    def binPaths = (mag_bins in List ? mag_bins : (mag_bins ? [mag_bins] : []))
    if (binPaths.size() > 1) {
        throw new IllegalArgumentException("LINK_SEQUENCE expects one MAG directory for ${meta.id}, got ${binPaths}")
    }
    def taxPaths = (host_taxonomy in List ? host_taxonomy : (host_taxonomy ? [host_taxonomy] : []))
    if (taxPaths.size() > 1) {
        throw new IllegalArgumentException("LINK_SEQUENCE expects one taxonomy file for ${meta.id}, got ${taxPaths}")
    }
    def shellQuote = { value -> "'" + value.toString().replace("'", "'\"'\"'") + "'" }
    def taxArg = taxPaths ? "--taxonomy ${shellQuote.call(taxPaths[0])}" : ''
    def binsArg = binPaths ? "--host-genomes ${shellQuote.call(binPaths[0])}" : ''
    """
    sequence_similarity_link.py \\
        --plasmid-contigs ${shellQuote.call(plasmid_contigs)} \\
        ${binsArg} ${taxArg} \\
        --sample-id ${shellQuote.call(meta.id)} \\
        --min-similarity ${params.link_min_similarity} \\
        --out ${shellQuote.call("${meta.id}.sequence_links.tsv")}
    """
}
