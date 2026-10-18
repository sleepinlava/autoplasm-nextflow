/*
 * Sequence similarity host-plasmid linking (TETRA tetranucleotide z-scores;
 * pipeline step: host_plasmid_link_sequence, implemented by
 * bin/sequence_similarity_link.R). Reads the actual staged MAG
 * directory; GTDB-Tk taxonomy is attached when available. Missing optional
 * inputs arrive as empty lists.
 */
process LINK_SEQUENCE {
    tag "${meta.id}"
    label 'process_low'
    conda "${projectDir}/envs/r_analysis.yml"
    // R 包集合以 envs/r_analysis.yml 为准；镜像需提供 data.table/vegan/Biostrings/Rsamtools
    container 'autoplasm-r-analysis:latest'

    publishDir "${params.outdir}/07_host_prediction/linking/sequence", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs), path(mag_bins, stageAs: 'mag_bins/*'), path(host_taxonomy)

    output:
    tuple val(meta), path("${meta.id}.sequence_links.tsv"), emit: links

    script:
    def binPaths = (mag_bins in List ? mag_bins : (mag_bins ? [mag_bins] : []))
    def taxPaths = (host_taxonomy in List ? host_taxonomy : (host_taxonomy ? [host_taxonomy] : []))
    def shellQuote = { value -> "'" + value.toString().replace("'", "'\"'\"'") + "'" }
    // MAG bins are a list of fastas staged under mag_bins/; the R script scans
    // that directory. GTDB-Tk emits one summary per domain (ar53 + bac120), so
    // merge them into a single taxonomy table with one header.
    def binsArg = binPaths ? "--host-genomes mag_bins" : ''
    def taxArg = taxPaths ? "--taxonomy taxonomy.tsv" : ''
    def taxList = taxPaths.collect { shellQuote.call(it) }.join(' ')
    def mergeTax = taxPaths ? "head -n 1 ${shellQuote.call(taxPaths[0])} > taxonomy.tsv && tail -q -n +2 ${taxList} >> taxonomy.tsv" : ''
    """
    ${mergeTax}
    sequence_similarity_link.R \\
        --plasmid-contigs ${shellQuote.call(plasmid_contigs)} \\
        ${binsArg} ${taxArg} \\
        --sample-id ${shellQuote.call(meta.id)} \\
        --min-similarity ${params.link_min_similarity} \\
        --out ${shellQuote.call("${meta.id}.sequence_links.tsv")}
    """
}
