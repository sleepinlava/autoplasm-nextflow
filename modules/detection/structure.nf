/*
 * Plasmid circularity / terminal-overlap detection (pipeline step:
 * plasmid_structure, implemented by bin/plasmid_structure.R with the
 * candidate circularity from explicit headers or direct terminal repeats).
 * Inverted repeats are retained as structural evidence, not circular calls.
 */
process PLASMID_STRUCTURE {
    tag { meta.id }
    label 'process_single'
    conda "${projectDir}/envs/r_analysis.yml"
    // R 包集合以 envs/r_analysis.yml 为准；镜像需提供 data.table/vegan/Biostrings/Rsamtools
    container 'autoplasm-r-analysis:latest'

    publishDir "${params.outdir}/04_plasmid_detection/structure", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)

    output:
    tuple val(meta), path("${meta.id}.plasmid_structure.tsv"), emit: structure
    tuple val("${task.process}"), val(meta), path("${meta.id}.PLASMID_STRUCTURE.task_command.sh"),
          val('Rscript --version'), eval('Rscript --version'),
          eval("sha256sum '${meta.id}.PLASMID_STRUCTURE.task_command.sh'"), emit: task_provenance

    script:
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.PLASMID_STRUCTURE.task_command.sh'
    plasmid_structure.R \\
        --contigs ${plasmid_contigs} \\
        --sample-id ${meta.id} \\
        --out ${meta.id}.plasmid_structure.tsv
    """
}
