/*
 * MetaBAT2 metagenomic binning for host MAGs (DAG node: mag_metabat2;
 * optional via params.mag_tools).
 */
process METABAT2 {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/mag.yml"

    publishDir "${params.outdir}/07_host_prediction/mag/${meta.id}/metabat2", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly), path(bam)

    output:
    tuple val(meta), path("metabat2_bins"), emit: bins

    script:
    """
    mkdir -p metabat2_bins
    jgi_summarize_bam_contig_depths --outputDepth depth.txt ${bam}
    metabat2 -i ${assembly} -a depth.txt -o metabat2_bins/bin
    """
}
