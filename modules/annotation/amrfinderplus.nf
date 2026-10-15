/*
 * AMRFinderPlus ARG/VF detection (DAG node: annotation_amrfinderplus; default
 * enabled). Requires the AMRFinderPlus database directory.
 */
process AMRFINDERPLUS {
    tag { meta.id }
    label 'process_low'
    conda "${projectDir}/envs/amrfinderplus.yml"

    publishDir "${params.outdir}/08_annotation/${meta.id}/amrfinderplus", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)
    path amrfinder_db

    output:
    tuple val(meta), path("${meta.id}.amrfinder.tsv"), emit: results

    script:
    """
    amrfinder -n ${plasmid_contigs} -d ${amrfinder_db} \\
        -o ${meta.id}.amrfinder.tsv --threads ${task.cpus}
    """
}
