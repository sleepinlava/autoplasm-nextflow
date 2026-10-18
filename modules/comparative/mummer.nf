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

    script:
    """
    nucmer --prefix ${meta.id} ${reference_plasmids} ${plasmid_contigs}
    show-coords -r ${meta.id}.delta > ${meta.id}.coords
    """
}
