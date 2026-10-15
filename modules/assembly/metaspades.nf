/*
 * metaSPAdes short-read metagenomic assembly (DAG node: assembly_metaspades;
 * alternative illumina assembler, also required for SCAPP graph analysis).
 */
process METASPADES {
    tag { meta.id }
    label 'process_highmem'
    conda "${projectDir}/envs/assembly_short.yml"

    publishDir "${params.outdir}/02_assembly/metaspades", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(read1), path(read2)

    output:
    tuple val(meta), path("${meta.id}.metaspades.contigs.fasta"), emit: assembly
    tuple val(meta), path("${meta.id}.assembly_graph.fastg"), emit: graph
    tuple val(meta), path("${meta.id}.spades_out"), emit: output_dir

    script:
    """
    metaspades.py -1 ${read1} -2 ${read2} -o ${meta.id}.spades_out -t ${task.cpus}
    cp ${meta.id}.spades_out/contigs.fasta ${meta.id}.metaspades.contigs.fasta
    cp ${meta.id}.spades_out/assembly_graph.fastg ${meta.id}.assembly_graph.fastg
    """
}
