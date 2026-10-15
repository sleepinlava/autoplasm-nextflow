/*
 * GTDB-Tk taxonomic classification of MAGs (DAG node: mag_gtdbtk; optional).
 * Requires the GTDB-Tk reference database.
 */
process GTDBTK {
    tag { meta.id }
    label 'process_highmem'
    conda "${projectDir}/envs/gtdbtk.yml"

    publishDir "${params.outdir}/07_host_prediction/mag/gtdbtk", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(mag_bins)
    path gtdbtk_db

    output:
    tuple val(meta), path("${meta.id}.gtdbtk_taxonomy.tsv"), emit: taxonomy
    tuple val(meta), path("${meta.id}.gtdbtk_out", type: 'dir'), emit: output_dir

    script:
    """
    export GTDBTK_DATA_PATH=${gtdbtk_db}
    gtdbtk classify_wf --genome_dir ${mag_bins} --out_dir ${meta.id}.gtdbtk_out \\
        --cpus ${task.cpus} --skip_ani_screen
    cat ${meta.id}.gtdbtk_out/gtdbtk.*.summary.tsv | grep -v '^user_genome' > body.tsv || true
    head -1 \$(ls ${meta.id}.gtdbtk_out/gtdbtk.*.summary.tsv | head -1) > header.tsv
    cat header.tsv body.tsv > ${meta.id}.gtdbtk_taxonomy.tsv
    """
}
