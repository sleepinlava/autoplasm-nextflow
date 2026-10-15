/*
 * Plasmid consensus builder (DAG node: plasmid_consensus; internal handler in
 * ABI, implemented here by bin/plasmid_consensus.py). Merges per-contig calls
 * from geNomad and the enabled optional tools with the configured strategy.
 */
process PLASMID_CONSENSUS {
    tag { meta.id }
    label 'process_low'
    conda "${projectDir}/envs/python.yml"

    publishDir "${params.outdir}/04_plasmid_detection/${meta.id}", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly), path(genomad_summary), path(extras)

    output:
    tuple val(meta), path("plasmid_contigs.fasta"), emit: contigs
    tuple val(meta), path("${meta.id}.plasmid_predictions.tsv"), emit: predictions
    tuple val(meta), path("${meta.id}.plasmid_consensus.tsv"), emit: consensus

    script:
    def extras_args = extras ? (extras instanceof List ? extras.collect { it.toString() } : [extras.toString()]).collect { "--extra ${it}" }.join(' ') : ''
    """
    plasmid_consensus.py \\
        --assembly ${assembly} \\
        --genomad-summary ${genomad_summary} \\
        ${extras_args} \\
        --method ${params.consensus_method} \\
        --weights "${params.consensus_weights}" \\
        --sample-id ${meta.id} \\
        --out-fasta plasmid_contigs.fasta \\
        --out-predictions ${meta.id}.plasmid_predictions.tsv \\
        --out-consensus ${meta.id}.plasmid_consensus.tsv
    """
}
