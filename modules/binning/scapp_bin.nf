/*
 * SCAPP plasmid reconstruction from the assembly graph (DAG node:
 * plasmid_binning_scapp; optional; requires graph + short reads).
 */
process SCAPP_BIN {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/scapp.yml"

    publishDir "${params.outdir}/05_plasmid_binning/scapp", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly_graph), path(read1), path(read2)

    output:
    tuple val(meta), path("${meta.id}.scapp_bin_out", type: 'dir'), emit: output_dir

    script:
    """
    scapp -g ${assembly_graph} -o ${meta.id}.scapp_bin_out -k 77 -p ${task.cpus} \\
        -r1 ${read1} -r2 ${read2}
    """
}
