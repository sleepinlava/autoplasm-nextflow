/*
 * Plasmid consensus builder (pipeline step: plasmid_consensus, implemented
 * by bin/plasmid_consensus.R). Merges per-contig calls
 * from geNomad and the enabled optional tools with the configured strategy;
 * the consensus table carries plasmidEC-style per-tool ensemble columns.
 */
process PLASMID_CONSENSUS {
    tag { meta.id }
    label 'process_low'
    conda "${projectDir}/envs/r_analysis.yml"
    // R 包集合以 envs/r_analysis.yml 为准；镜像需提供 data.table/vegan/Biostrings/Rsamtools
    container 'autoplasm-r-analysis:latest'

    publishDir "${params.outdir}/04_plasmid_detection/consensus", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly), path(genomad_summary), path(extras)

    output:
    tuple val(meta), path("${meta.id}.plasmid_contigs.fasta"), emit: contigs
    tuple val(meta), path("${meta.id}.plasmid_predictions.tsv"), emit: predictions
    tuple val(meta), path("${meta.id}.plasmid_consensus.tsv"), emit: consensus

    script:
    def extras_args = extras ? (extras in List ? extras.collect { it.toString() } : [extras.toString()]).collect { "--extra ${it}" }.join(' ') : ''
    def domain_args = meta.analysis_entity == 'gplas_graph_node' ? '--include-all-contigs true' : ''
    """
    plasmid_consensus.R \\
        --assembly ${assembly} \\
        --genomad-summary ${genomad_summary} \\
        ${extras_args} \\
        --method ${params.consensus_method} \\
        --weights "${params.consensus_weights}" \\
        ${domain_args} \\
        --sample-id ${meta.id} \\
        --out-fasta ${meta.id}.plasmid_contigs.fasta \\
        --out-predictions ${meta.id}.plasmid_predictions.tsv \\
        --out-consensus ${meta.id}.plasmid_consensus.tsv
    """
}
