/*
 * hybridSPAdes hybrid metagenomic assembly (DAG node: assembly_hybridspades;
 * alternative hybrid assembler).
 */
process HYBRIDSPADES {
    tag { meta.id }
    label 'process_highmem'
    conda "${projectDir}/envs/assembly_hybrid.yml"

    publishDir "${params.outdir}/02_assembly/${meta.id}", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(read1), path(read2), path(long_reads)

    output:
    tuple val(meta), path("contigs.fasta"), emit: assembly
    tuple val(meta), path("spades_out"), emit: output_dir

    script:
    """
    spades.py -1 ${read1} -2 ${read2} --nanopore ${long_reads} --meta \\
        -o spades_out -t ${task.cpus}
    cp spades_out/contigs.fasta contigs.fasta
    """
}
