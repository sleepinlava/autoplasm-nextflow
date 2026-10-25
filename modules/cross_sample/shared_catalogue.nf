/* Sequence identity only: complete DNA or reverse complement, not families. */
process SHARED_CATALOGUE {
    tag 'shared_nucleotide_reference'
    label 'process_single'
    conda "${moduleDir}/../../envs/catalogue.yml"
    container 'python:3.12-slim'

    publishDir "${params.outdir}/10_abundance/shared_reference", mode: params.publish_dir_mode

    input:
    tuple val(sample_ids), path(assemblies, stageAs: 'assemblies??/*'), path(plasmids, stageAs: 'plasmids??/*')
    val expected_samples

    path code_assets, stageAs: 'source_assets/*'

    output:
    path 'catalogue', emit: catalogue

    script:
    def quoted = { values -> (values instanceof List ? values : [values])
        .collect { "'" + it.toString().replace("'", "'\"'\"'") + "'" }.join(' ') }
    """
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    python3 analysis_code/build_shared_catalogue.py \\
        --sample-ids ${quoted.call(sample_ids)} \\
        --assemblies ${quoted.call(assemblies)} \\
        --plasmids ${quoted.call(plasmids)} \\
        --out-dir catalogue --expected-samples ${expected_samples}
    """
}
