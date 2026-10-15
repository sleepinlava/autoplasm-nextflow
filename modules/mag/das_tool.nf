/*
 * DAS Tool meta-binner aggregation (DAG node: mag_das_tool; optional).
 * Aggregates MetaBAT2 bins (and CONCOCT output when enabled).
 */
process DAS_TOOL {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/mag.yml"

    publishDir "${params.outdir}/07_host_prediction/mag/${meta.id}/das_tool", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly), path(binner_dirs)

    output:
    tuple val(meta), path("das_tool_out"), emit: output_dir

    script:
    def inputs = (binner_dirs instanceof List ? binner_dirs : [binner_dirs]).collect { it.toString() }.join(',')
    """
    DAS_Tool --inputbasenames ${inputs} --contigs ${assembly} \\
        --outputbasename das_tool_out/${meta.id} --threads ${task.cpus} \\
        --createDirectory 2>/dev/null || \\
    DAS_Tool -i ${inputs} -c ${assembly} -o das_tool_out/${meta.id} -t ${task.cpus}
    """
}
