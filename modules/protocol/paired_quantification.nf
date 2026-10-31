process PROTOCOL_PAIRED_QUANTIFICATION {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/paired_quantification.yml"
    publishDir "${params.outdir}/10_abundance/paired", mode: params.publish_dir_mode,
        saveAs: { name -> name.endsWith('.bam') || name.endsWith('.bai') ? null : name }
    cache 'deep'
    input:
    tuple val(meta), path(bam)
    path catalogue
    path code_assets,stageAs:'source_assets/*'
    output:
    path("*.task_command.sh"), emit: commands
    tuple val(meta), path("${meta.id}.paired.coverm.tsv"), emit: coverage
    tuple val(meta), path("${meta.id}.paired.tsv"), emit: measurements
    tuple val(meta), path("${meta.id}.paired.mapping_stats.json"), emit: mapping_stats
    tuple val(meta), path("${meta.id}.qualified.bam"), emit: qualified_bam, optional:true
    tuple val(meta), path("${meta.id}.qualified.bam.bai"), emit: qualified_index, optional:true
    script:
    def retained = params.protocol_strain ? "--filtered-bam '${meta.id}.qualified.bam'" : ''
    """
    cp -- "\${BASH_SOURCE[0]}" "${meta.id}.${task.process.tokenize(':').last()}.task_command.sh"
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    export PYTHONPATH=\$PWD/analysis_code
    python3 analysis_code/protocol_quantification.py --bam ${bam} --catalogue ${catalogue} --sample '${meta.id}' --output '${meta.id}.paired.tsv' --max-mismatch-rate ${params.protocol_max_mismatch_rate} ${retained}
    """
}
