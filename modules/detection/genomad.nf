/*
 * geNomad plasmid/virus classification (DAG node: plasmid_detect_genomad;
 * mandatory on all platforms). Requires the geNomad database.
 */
process GENOMAD {
    tag { meta.id }
    label 'process_high'
    conda "${projectDir}/envs/genomad.yml"

    publishDir "${params.outdir}/04_plasmid_detection/genomad", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly)
    path genomad_db

    output:
    tuple val(meta), path("${meta.id}_summary/${meta.id}_plasmid_summary.tsv"), emit: plasmid_summary
    tuple val(meta), path("${meta.id}_summary/${meta.id}_plasmid.fna"), emit: plasmid_contigs
    tuple val(meta), path("${meta.id}_summary/${meta.id}_virus_summary.tsv"), emit: virus_summary
    tuple val(meta), path("${meta.id}.genomad_out", type: 'dir'), emit: output_dir

    script:
    def prefix = assembly.name.replaceAll(/\.(fasta|fa|fna)$/, '')
    """
    genomad end-to-end --cleanup --restart --threads ${task.cpus} \\
        ${assembly} ${meta.id}.genomad_out ${genomad_db}
    mv ${meta.id}.genomad_out/${prefix}_summary ./${meta.id}_summary
    """
}
