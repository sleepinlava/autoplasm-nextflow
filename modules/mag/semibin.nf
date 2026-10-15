/*
 * SemiBin deep-learning metagenomic binning (DAG node: mag_semibin; optional).
 */
process SEMIBIN {
    tag { meta.id }
    label 'process_high'
    conda "${projectDir}/envs/semibin.yml"

    publishDir "${params.outdir}/07_host_prediction/mag/semibin", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly), path(bam)

    output:
    tuple val(meta), path("${meta.id}.semibin_out", type: 'dir'), emit: output_dir

    script:
    """
    SemiBin2 single_easy_bin --input_contigs ${assembly} --input_bam ${bam} \\
        --output ${meta.id}.semibin_out --threads ${task.cpus}
    """
}
