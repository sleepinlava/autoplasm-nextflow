/*
 * MOB-recon plasmid reconstruction (DAG node: plasmid_binning_mob_recon;
 * optional). Requires the MOB-suite database.
 */
process MOB_RECON {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/mob_suite.yml"

    publishDir "${params.outdir}/05_plasmid_binning/${meta.id}/mob_recon", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)
    path mob_db

    output:
    tuple val(meta), path("mob_recon_out"), emit: output_dir

    script:
    """
    mob_recon --infile ${plasmid_contigs} --outdir mob_recon_out \\
        --num_threads ${task.cpus} --database_directory ${mob_db}
    """
}
