/*
 * PlasMAAG multi-sample graph-based plasmid binning (DAG node:
 * plasmid_binning_plasmaag; optional, params.plasmid_binning_tools).
 */
process PLASMAAG {
    tag { meta.id }
    label 'process_high'
    conda "${projectDir}/envs/plasmaag.yml"

    publishDir "${params.outdir}/05_plasmid_binning/${meta.id}/plasmaag", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs), path(reads_contigs_table)

    output:
    tuple val(meta), path("plasmaag_out"), emit: bins

    script:
    """
    plasmaag --reads_and_contigs ${reads_contigs_table} \\
        --output plasmaag_out --threads ${task.cpus}
    """
}
