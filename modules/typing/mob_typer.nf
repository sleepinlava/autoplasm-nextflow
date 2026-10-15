/*
 * MOB-typer relaxase/MOB/oriT typing (DAG node: typing_mob_typer; default
 * enabled). Requires the MOB-suite database.
 */
process MOB_TYPER {
    tag { meta.id }
    label 'process_low'
    conda "${projectDir}/envs/typing.yml"

    publishDir "${params.outdir}/06_plasmid_typing/mob_typer", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)
    path mob_db

    output:
    tuple val(meta), path("${meta.id}.mob_typer.tsv"), emit: typing

    script:
    """
    mob_typer --infile ${plasmid_contigs} --out_file ${meta.id}.mob_typer.tsv \\
        --database_directory ${mob_db} --num_threads ${task.cpus} --multi
    """
}
