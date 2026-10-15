/*
 * DAS Tool meta-binner aggregation (DAG node: mag_das_tool; optional).
 * Aggregates MetaBAT2 bins (and CONCOCT output when enabled).
 */
process DAS_TOOL {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/mag.yml"

    publishDir "${params.outdir}/07_host_prediction/mag/das_tool", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly), path(binner_dirs)

    output:
    tuple val(meta), path("${meta.id}.das_tool_out", type: 'dir'), emit: output_dir

    script:
    def inputs = (binner_dirs in List ? binner_dirs : [binner_dirs]).collect { it.toString() }.join(',')
    """
    mkdir -p ${meta.id}.das_tool_out
    DAS_Tool -i ${inputs} -c ${assembly} -o ${meta.id}.das_tool_out/${meta.id} -t ${task.cpus}
    """
}
