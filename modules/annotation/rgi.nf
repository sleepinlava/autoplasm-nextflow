/*
 * RGI/CARD resistance gene identification (DAG node: annotation_rgi; optional
 * via params.annotation_optional_tools). Requires the CARD database.
 */
process RGI {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/rgi.yml"

    publishDir "${params.outdir}/08_annotation/rgi", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)
    path card_db

    output:
    tuple val(meta), path("${meta.id}.rgi_out", type: 'dir'), emit: output_dir

    script:
    """
    mkdir -p ${meta.id}.rgi_out
    rgi load --card_json ${card_db} --local 2>/dev/null || true
    rgi main --input_sequence ${plasmid_contigs} \\
        --output_file ${meta.id}.rgi_out/${meta.id}.rgi \\
        --input_type contig --num_threads ${task.cpus} --local
    """
}
