process ANCOMBC2 {
    label 'process_medium'
    conda "${projectDir}/envs/ancombc2.yml"
    publishDir "${params.outdir}/11_diversity/ancombc2", mode: params.publish_dir_mode
    cache 'deep'
    input:
    path abundance, stageAs:'abundance/*'
    path metadata, stageAs:'metadata/*'
    path code_assets,stageAs:'source_assets/*'
    output:
    path("${prefix}ancombc2"), emit: results
    path('ANCOMBC2.task_command.sh'), emit: commands
    script:
    prefix = params.short_read_protocol ? (task.process.tokenize(':').last() == 'SYSTEM_ANCOMBC2' ? 'systems.' : 'plasmids.') : ''
    def q = { v -> "'" + v.toString().replace("'", "'\"'\"'") + "'" }
    """
    cp -- "\${BASH_SOURCE[0]}" ANCOMBC2.task_command.sh
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    Rscript analysis_code/ancombc2_plasmid.R --abundance ${abundance} --metadata ${metadata} --output '${prefix}ancombc2' \\
        --formula ${q.call(params.ancombc2_formula)} --random ${q.call(params.ancombc2_random_formula ?: '')} \\
        --prevalence ${params.ancombc2_prevalence} --replicates ${params.min_group_replicates} --threads ${task.cpus}
    """
}
