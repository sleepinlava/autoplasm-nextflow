/*
 * metaSPAdes short-read metagenomic assembly (DAG node: assembly_metaspades;
 * alternative illumina assembler, also required for SCAPP graph analysis).
 */
process METASPADES {
    tag { meta.id }
    label 'process_highmem'
    conda "${projectDir}/envs/assembly_short.yml"

    publishDir "${params.outdir}/02_assembly/${meta.id}", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(read1), path(read2)

    output:
    tuple val(meta), path("contigs.fasta"), emit: assembly
    tuple val(meta), path("assembly_graph.fastg"), emit: graph
    tuple val(meta), path("spades_out"), emit: output_dir

    script:
    """
    metaspades.py -1 ${read1} -2 ${read2} -o spades_out -t ${task.cpus}
    cp spades_out/contigs.fasta contigs.fasta
    cp spades_out/assembly_graph.fastg assembly_graph.fastg
    """
}
