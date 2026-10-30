process STATISTICS_INPUTS {
    tag 'statistics_input_validation'
    label 'process_single'
    conda "${moduleDir}/../../envs/catalogue.yml"
    container 'python:3.12-slim'
    publishDir "${params.outdir}/tables/statistics_inputs", mode: params.publish_dir_mode,
        saveAs: { filename -> filename.tokenize('/').last() }
    input:
    path(contigs, stageAs: 'contigs/*')
    path(plasmids, stageAs: 'plasmids/*')
    path(states, stageAs: 'states/*')
    path(metadata, stageAs: 'cohort/*')
    val expected_samples
    path code_assets, stageAs: 'source_assets/*'

    output:
    path 'validated/contig_abundance.tsv', emit: contigs
    path 'validated/plasmid_abundance.tsv', emit: plasmids
    path 'validated/samples.tsv', emit: metadata
    path 'validated/sample_states.tsv', emit: states
    path 'validated/validation.json', emit: validation
    tuple val("${task.process}"), path("STATISTICS_INPUTS.task_command.sh"),
          val('python3 analysis_code/validate_statistics_inputs.py -h'), eval('python3 analysis_code/validate_statistics_inputs.py -h'),
          eval("sha256sum 'STATISTICS_INPUTS.task_command.sh'"),
          eval("cut -f1 cohort/* | tail -n +2 | sort -u | paste -sd, -"), emit: cohort_provenance

    script:
    """
    cp -- "\${BASH_SOURCE[0]}" 'STATISTICS_INPUTS.task_command.sh'
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    python3 analysis_code/validate_statistics_inputs.py \\
      --contigs ${contigs} --plasmids ${plasmids} --states ${states} \\
      --metadata ${metadata} --expected-samples ${expected_samples} --out-dir validated
    """
}
