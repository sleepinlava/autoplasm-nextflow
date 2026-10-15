/*
 * eggNOG-mapper functional annotation (DAG node: annotation_eggnog_mapper;
 * optional via params.annotation_optional_tools). Requires the eggNOG
 * database (EGGNOG_DATA_DIR).
 */
process EGGNOG_MAPPER {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/eggnog.yml"

    publishDir "${params.outdir}/08_annotation/eggnog", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)
    path eggnog_db

    output:
    tuple val(meta), path("${meta.id}.eggnog_out", type: 'dir'), emit: output_dir

    script:
    """
    mkdir -p ${meta.id}.eggnog_out
    emapper.py -i ${plasmid_contigs} --output ${meta.id}.eggnog_out/${meta.id}.eggnog \\
        --cpu ${task.cpus} --data_dir ${eggnog_db}
    """
}
