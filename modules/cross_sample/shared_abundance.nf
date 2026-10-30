process SHARED_ABUNDANCE_TABLES {
    tag 'shared_reference_measurements'
    label 'process_single'
    conda "${moduleDir}/../../envs/catalogue.yml"
    container 'python:3.12-slim'
    publishDir "${params.outdir}/tables", mode: params.publish_dir_mode,
        saveAs: { filename -> filename.tokenize('/').last() }

    input:
    path catalogue
    tuple val(sample_ids), path(tables, stageAs: 'measurements??/*')
    val mapper

    path code_assets, stageAs: 'source_assets/*'

    output:
    path 'quantification/contig_abundance.tsv', emit: contigs
    path 'quantification/plasmid_abundance.tsv', emit: plasmids
    path 'quantification/sample_states.tsv', emit: states
    path 'quantification/method.json', emit: method
    tuple val("${task.process}"), path("SHARED_ABUNDANCE_TABLES.task_command.sh"),
          val('python3 analysis_code/collect_shared_abundance.py -h'), eval('python3 analysis_code/collect_shared_abundance.py -h'),
          eval("sha256sum 'SHARED_ABUNDANCE_TABLES.task_command.sh'"),
          eval("cut -f1 quantification/sample_states.tsv | tail -n +2 | paste -sd, -"), emit: cohort_provenance

    script:
    def quoted = { values -> (values instanceof List ? values : [values])
        .collect { "'" + it.toString().replace("'", "'\"'\"'") + "'" }.join(' ') }
    """
    cp -- "\${BASH_SOURCE[0]}" 'SHARED_ABUNDANCE_TABLES.task_command.sh'
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    python3 analysis_code/collect_shared_abundance.py \\
        --catalogue ${catalogue} --sample-ids ${quoted.call(sample_ids)} \\
        --tables ${quoted.call(tables)} --mapper '${mapper}' --out-dir quantification
    """
}
