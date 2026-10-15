/*
 * Medaka consensus polishing of ONT assemblies (DAG node: polishing_medaka;
 * optional, enabled via params.polishing_tools).
 */
process MEDAKA {
    tag { meta.id }
    label 'process_high'
    conda "${projectDir}/envs/assembly_ont.yml"

    publishDir "${params.outdir}/03_assembly_qc/polishing/${meta.id}", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly), path(long_reads)

    output:
    tuple val(meta), path("consensus.fasta"), emit: assembly
    tuple val(meta), path("medaka_out"), emit: output_dir

    script:
    """
    medaka_consensus -i ${long_reads} -d ${assembly} -o medaka_out -t ${task.cpus}
    cp medaka_out/consensus.fasta consensus.fasta
    """
}
