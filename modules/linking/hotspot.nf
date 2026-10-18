/*
 * HOTSPOT Transformer host prediction (optional high-confidence host-linking
 * module; Ji et al. 2023, Bioinformatics 39(5):btad283;
 * https://github.com/Orin-beep/HOTSPOT). HOTSPOT is not packaged for
 * bioconda, so this module expects a cloned HOTSPOT repository
 * (--hotspot_home) plus the downloaded database/ and models/ folders
 * (--hotspot_db / --hotspot_models; see the HOTSPOT README's prepare_db.sh
 * and prepare_mdl.sh). host_lineage.tsv is converted to the host-link schema;
 * host_id is the deepest predicted taxonomic level (species -> phylum).
 */
process LINK_HOTSPOT {
    tag "${meta.id}"
    label 'process_medium'
    conda "${projectDir}/envs/hotspot.yml"

    publishDir "${params.outdir}/07_host_prediction/linking/hotspot", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)

    output:
    tuple val(meta), path("${meta.id}.hotspot_links.tsv"), emit: links
    tuple val(meta), path("${meta.id}.host_lineage.tsv"), emit: lineage

    script:
    """
    python3 ${params.hotspot_home}/preprocessing.py \\
        --fasta ${plasmid_contigs} \\
        --database ${params.hotspot_db} \\
        --model_path ${params.hotspot_models} \\
        --midfolder hotspot_tmp \\
        --threads ${task.cpus}
    python3 ${params.hotspot_home}/hotspot.py \\
        --model_path ${params.hotspot_models} \\
        --midfolder hotspot_tmp \\
        --out hotspot_results \\
        --device cpu \\
        --threads ${task.cpus}
    awk 'BEGIN { FS = OFS = "\\t" }
         NR == 1 {
           print "plasmid_id", "host_id", "sample_id", "evidence_type", "score", "supporting_data"
           next
         }
         {
           host = ""; lineage = ""
           for (i = 2; i <= 7; i++) {
             if (\$i != "-" && \$i != "")
               lineage = (lineage == "" ? \$i : lineage ">" \$i)
           }
           for (i = 7; i >= 2; i--) {
             if (\$i != "-" && \$i != "") { host = \$i; break }
           }
           if (host != "")
             print \$1, host, "${meta.id}", "hotspot", "", "method=hotspot;lineage=" lineage
         }' hotspot_results/host_lineage.tsv > ${meta.id}.hotspot_links.tsv
    cp hotspot_results/host_lineage.tsv ${meta.id}.host_lineage.tsv
    """
}
