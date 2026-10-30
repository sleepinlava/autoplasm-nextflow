/*
 * Long-read bridge evidence host-plasmid linking (pipeline step:
 * host_plasmid_link_longread, implemented by bin/longread_bridge_link.R).
 * Reads spanning a plasmid contig and another
 * (host) contig in the contig-alignment BAM are counted as bridge evidence.
 * Rsamtools scans the BAM directly, so no samtools step is needed.
 */
process LINK_LONGREAD {
    tag "${meta.id}"
    label 'process_low'
    conda "${projectDir}/envs/r_analysis.yml"
    // R 包集合以 envs/r_analysis.yml 为准；镜像需提供 data.table/vegan/Biostrings/Rsamtools
    container 'autoplasm-r-analysis:latest'

    publishDir "${params.outdir}/07_host_prediction/linking/longread", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs), path(assembly), path(bam)

    output:
    tuple val(meta), path("${meta.id}.longread_bridge_links.tsv"), emit: links
    tuple val("${task.process}"), val(meta), path("${meta.id}.LINK_LONGREAD.task_command.sh"),
          val('Rscript --version'), eval('Rscript --version'),
          eval("sha256sum '${meta.id}.LINK_LONGREAD.task_command.sh'"), emit: task_provenance


    script:
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.LINK_LONGREAD.task_command.sh'
    longread_bridge_link.R \\
        --sam ${bam} \\
        --plasmid-contigs ${plasmid_contigs} \\
        --assembly ${assembly} \\
        --sample-id ${meta.id} \\
        --out ${meta.id}.longread_bridge_links.tsv
    """
}
