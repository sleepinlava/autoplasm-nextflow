/*
 * SCAPP assembly-graph plasmid detection (DAG node: plasmid_detect_scapp;
 * optional, illumina + metaSPAdes graph only).
 */
process SCAPP_DETECT {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/scapp.yml"

    publishDir "${params.outdir}/04_plasmid_detection/scapp", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly_graph), path(read1), path(read2)

    output:
    tuple val(meta), path("${meta.id}.scapp.fasta"), emit: predictions
    tuple val(meta), path("${meta.id}.scapp_out", type: 'dir'), emit: output_dir

    script:
    """
    scapp -g ${assembly_graph} -o ${meta.id}.scapp_out -k 77 -p ${task.cpus} \\
        -r1 ${read1} -r2 ${read2}
    touch ${meta.id}.scapp.fasta
    for f in ${meta.id}.scapp_out/*.confident_cycs.fasta; do
        [ -f "\$f" ] && cat "\$f" >> ${meta.id}.scapp.fasta
    done
    """
}
