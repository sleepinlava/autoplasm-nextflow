/*
 * Long-read bridge evidence host-plasmid linking (DAG node:
 * host_plasmid_link_longread; internal handler in ABI, implemented here by
 * bin/longread_bridge_link.py). Reads spanning a plasmid contig and another
 * (host) contig in the contig-alignment BAM are counted as bridge evidence.
 */
process LINK_LONGREAD {
    tag { meta.id }
    label 'process_low'
    conda "${projectDir}/envs/abundance.yml"

    publishDir "${params.outdir}/07_host_prediction/linking/longread", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs), path(assembly), path(bam)

    output:
    tuple val(meta), path("${meta.id}.longread_bridge_links.tsv"), emit: links

    script:
    """
    samtools view ${bam} > alignments.sam
    longread_bridge_link.py \\
        --sam alignments.sam \\
        --plasmid-contigs ${plasmid_contigs} \\
        --assembly ${assembly} \\
        --sample-id ${meta.id} \\
        --out ${meta.id}.longread_bridge_links.tsv
    """
}
