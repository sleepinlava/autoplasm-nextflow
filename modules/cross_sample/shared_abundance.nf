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

    script:
    def quoted = { values -> (values instanceof List ? values : [values])
        .collect { "'" + it.toString().replace("'", "'\"'\"'") + "'" }.join(' ') }
    """
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    python3 analysis_code/collect_shared_abundance.py \\
        --catalogue ${catalogue} --sample-ids ${quoted.call(sample_ids)} \\
        --tables ${quoted.call(tables)} --mapper '${mapper}' --out-dir quantification
    """
}
