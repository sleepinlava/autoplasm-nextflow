/*
 * MEGAHIT short-read metagenomic assembly (DAG node: assembly_megahit;
 * default illumina assembler). Memory is capped explicitly to mirror the ABI
 * behaviour of constraining MEGAHIT below cgroup limits.
 */
process MEGAHIT {
    tag { meta.id }
    label 'process_highmem'
    conda "${projectDir}/envs/assembly_short.yml"

    publishDir "${params.outdir}/02_assembly/${meta.id}", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(read1), path(read2)

    output:
    tuple val(meta), path("final.contigs.fa"), emit: assembly
    tuple val(meta), path("megahit_out"), emit: output_dir

    script:
    def memory_bytes = params.megahit_memory_bytes
    """
    megahit -1 ${read1} -2 ${read2} -o megahit_out -t ${task.cpus} --memory ${memory_bytes}
    cp megahit_out/final.contigs.fa final.contigs.fa
    """
}
