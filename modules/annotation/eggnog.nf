/*
 * eggNOG-mapper functional annotation (DAG node: annotation_eggnog_mapper;
 * optional via params.annotation_optional_tools). Requires the eggNOG
 * database (EGGNOG_DATA_DIR).
 */
process EGGNOG_MAPPER {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/eggnog.yml"

    publishDir "${params.outdir}/08_annotation/${meta.id}/eggnog", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)
    path eggnog_db

    output:
    tuple val(meta), path("eggnog_out"), emit: output_dir

    script:
    """
    mkdir -p eggnog_out
    emapper.py -i ${plasmid_contigs} --output eggnog_out/${meta.id}.eggnog \\
        --cpu ${task.cpus} --data_dir ${eggnog_db}
    """
}
