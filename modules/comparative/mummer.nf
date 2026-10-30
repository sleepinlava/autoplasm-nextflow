/*
 * MUMmer/nucmer whole-genome plasmid alignment (pipeline step:
 * comparative_mummer; optional via params.comparative_optional_tools).
 * Requires a reference plasmid FASTA.
 */
process MUMMER {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/comparative.yml"
    container 'quay.io/biocontainers/mummer:3.23--pl5321h503566f_21'

    publishDir "${params.outdir}/09_comparative_genomics/mummer", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)
    path reference_plasmids

    output:
    tuple val(meta), path("${meta.id}.coords"), emit: coords
    tuple val("${task.process}"), val(meta), path("${meta.id}.MUMMER.task_command.sh"),
          val('nucmer --version'), eval('nucmer --version 2>&1 | sed -n "1p"'),
          eval("sha256sum '${meta.id}.MUMMER.task_command.sh'"), emit: task_provenance

    script:
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.MUMMER.task_command.sh'
    nucmer --prefix ${meta.id} ${reference_plasmids} ${plasmid_contigs}
    show-coords -r ${meta.id}.delta > ${meta.id}.coords
    """
}
