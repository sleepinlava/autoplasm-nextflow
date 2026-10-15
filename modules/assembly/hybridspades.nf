/*
 * hybridSPAdes hybrid metagenomic assembly (DAG node: assembly_hybridspades;
 * alternative hybrid assembler).
 */
process HYBRIDSPADES {
    tag { meta.id }
    label 'process_highmem'
    conda "${projectDir}/envs/assembly_hybrid.yml"

    publishDir "${params.outdir}/02_assembly/hybridspades", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(read1), path(read2), path(long_reads)

    output:
    tuple val(meta), path("${meta.id}.hybridspades.contigs.fasta"), emit: assembly
    tuple val(meta), path("${meta.id}.spades_out"), emit: output_dir

    script:
    """
    spades.py -1 ${read1} -2 ${read2} --nanopore ${long_reads} --meta \\
        -o ${meta.id}.spades_out -t ${task.cpus}
    cp ${meta.id}.spades_out/contigs.fasta ${meta.id}.hybridspades.contigs.fasta
    """
}
