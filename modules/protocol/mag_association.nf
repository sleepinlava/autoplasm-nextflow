process PROTOCOL_MAG_TABLES {
    label 'process_single'
    conda "${projectDir}/envs/catalogue.yml"
    container 'python:3.12-slim'
    publishDir "${params.outdir}/07_host_prediction/mag", mode: params.publish_dir_mode
    cache 'deep'
    input:
    tuple val(samples), path(bins, stageAs:'bins??/*'), path(quality,stageAs:'quality??/*'), path(taxonomy,stageAs:'taxonomy??/*')
    path catalogue
    path abundance
    path code_assets,stageAs:'source_assets/*'
    output:
    path("*.task_command.sh"), emit: commands
    path('mags'), emit: measurements
    script:
    def bin_dirs = bins instanceof List ? bins : [bins]
    def quality_files = quality instanceof List ? quality : [quality]
    def tax_dirs = taxonomy instanceof List ? taxonomy : [taxonomy]
    def spec = samples.withIndex().collect { sample,i -> [sample_id:sample.id,bins:bin_dirs[i].resolve('cellular').listFiles().findAll { it.name.endsWith('.fna') }.collect { it.toString() },quality:quality_files[i].toString(),taxonomy:tax_dirs[i].listFiles().findAll { it.name.endsWith('.summary.tsv') }.collect { it.toString() }] }
    """
    cp -- "\${BASH_SOURCE[0]}" "${task.process.tokenize(':').last()}.task_command.sh"
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    export PYTHONPATH=\$PWD/analysis_code
    cat > spec.json <<'SPEC'
${groovy.json.JsonOutput.toJson(spec)}
SPEC
    python3 analysis_code/protocol_hosts.py mags --spec spec.json --catalogue '${catalogue}' --abundance '${abundance}' --output mags \\
      --min-completeness ${params.protocol_mag_min_completeness} --max-contamination ${params.protocol_mag_max_contamination} --min-locus-fraction ${params.protocol_strain_min_locus_fraction}
    """
}
process PROTOCOL_HOST_MATRIX {
    label 'process_single'
    conda "${projectDir}/envs/catalogue.yml"
    container 'python:3.12-slim'
    publishDir "${params.outdir}/07_host_prediction/association", mode: params.publish_dir_mode
    cache 'deep'
    input:
    path plasmids
    path mags
    path metadata
    path code_assets,stageAs:'source_assets/*'
    output:
    path("*.task_command.sh"), emit: commands
    path('host_matrices'), emit: matrices
    script:
    def q = { v -> "'"+v.toString().replace("'","'\"'\"'")+"'" }
    """
    cp -- "\${BASH_SOURCE[0]}" "${task.process.tokenize(':').last()}.task_command.sh"
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    export PYTHONPATH=\$PWD/analysis_code
    python3 analysis_code/protocol_hosts.py host_matrix --plasmids '${plasmids}' --mags '${mags}' --metadata '${metadata}' --output host_matrices \\
      --strata ${q.call(params.protocol_host_strata)} --subject ${q.call(params.protocol_host_subject ?: '')} \\
      --min-samples ${params.network_min_samples} --prevalence ${params.ancombc2_prevalence}
    """
}
process PROTOCOL_HOST_FASTSPAR {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/network.yml"
    container 'quay.io/biocontainers/fastspar:1.0.0--h1b620e3_6'
    publishDir "${params.outdir}/07_host_prediction/association", mode: params.publish_dir_mode
    input:
    tuple val(meta), path(matrix)
    output:
    path("*.task_command.sh"), emit: commands
    tuple val(meta), path("${meta.id}"), emit: association
    script:
    """
    cp -- "\${BASH_SOURCE[0]}" "${meta.id}.${task.process.tokenize(':').last()}.task_command.sh"
    mkdir '${meta.id}' bootstrap_counts bootstrap_correlation
    fastspar --otu_table '${matrix}' --correlation '${meta.id}/correlation.tsv' \\
      --covariance '${meta.id}/covariance.tsv' --threads ${task.cpus} --seed 20261030
    fastspar_bootstrap --otu_table '${matrix}' --number ${params.protocol_host_bootstraps} --prefix bootstrap_counts/otu --seed 20261030
    for counts in bootstrap_counts/*; do
      name=\$(basename "\$counts")
      fastspar --otu_table "\$counts" --correlation "bootstrap_correlation/cor_\$name" \\
        --covariance "bootstrap_correlation/cov_\$name" --iterations 5 --threads ${task.cpus} --seed 20261030
    done
    fastspar_pvalues --otu_table '${matrix}' --correlation '${meta.id}/correlation.tsv' \\
      --prefix bootstrap_correlation/cor_otu_ --permutations ${params.protocol_host_bootstraps} --outfile '${meta.id}/pvalues.tsv'
    fastspar --version > '${meta.id}/version.txt' 2>&1
    """
}
process PROTOCOL_HOST_EDGES {
    label 'process_single'
    conda "${projectDir}/envs/catalogue.yml"
    container 'python:3.12-slim'
    publishDir "${params.outdir}/07_host_prediction/association", mode: params.publish_dir_mode
    cache 'deep'
    input:
    tuple val(meta), path(association)
    path code_assets,stageAs:'source_assets/*'
    output:
    path("*.task_command.sh"), emit: commands
    path("${meta.id}.host_edges.tsv"), emit: edges
    script:
    """
    cp -- "\${BASH_SOURCE[0]}" "${meta.id}.${task.process.tokenize(':').last()}.task_command.sh"
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    export PYTHONPATH=\$PWD/analysis_code
    python3 analysis_code/protocol_hosts.py host_edges --correlation '${association}/correlation.tsv' --pvalues '${association}/pvalues.tsv' \\
      --output '${meta.id}.host_edges.tsv' --stratum '${meta.id}' --min-correlation ${params.link_min_correlation}
    """
}
