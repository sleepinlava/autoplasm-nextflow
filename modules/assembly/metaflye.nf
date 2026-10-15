/*
 * metaFlye long-read metagenomic assembly (DAG node: assembly_metaflye;
 * mandatory ont assembler).
 */
process METAFLYE {
    tag { meta.id }
    label 'process_highmem'
    conda "${projectDir}/envs/assembly_ont.yml"

    publishDir "${params.outdir}/02_assembly/${meta.id}", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(long_reads)

    output:
    tuple val(meta), path("assembly.fasta"), emit: assembly
    tuple val(meta), path("assembly_graph.gfa"), emit: graph
    tuple val(meta), path("flye_out"), emit: output_dir

    script:
    """
    flye --meta --nano-raw ${long_reads} --out-dir flye_out --threads ${task.cpus}
    cp flye_out/assembly.fasta assembly.fasta
    cp flye_out/assembly_graph.gfa assembly_graph.gfa
    """
}
