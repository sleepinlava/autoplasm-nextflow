/*
 * ISEScan insertion sequence detection (DAG node: annotation_isescan; default
 * enabled per config_default.yaml).
 */
process ISESCAN {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/annotation.yml"
    container 'quay.io/biocontainers/isescan:1.7.3--hab16a5f_1'

    publishDir "${params.outdir}/08_annotation/isescan", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)

    output:
    tuple val(meta), path("${meta.id}.isescan_out", type: 'dir'), emit: results

    script:
    """
    isescan.py --seqfile ${plasmid_contigs} --output ${meta.id}.isescan_out \\
        --nthread ${task.cpus}
    """
}
