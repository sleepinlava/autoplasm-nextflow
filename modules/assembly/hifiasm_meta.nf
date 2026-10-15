/*
 * hifiasm-meta HiFi metagenomic assembly (DAG node: assembly_hifiasm).
 * The conda package provides hifiasm with metagenomics support (the ABI
 * registry uses the same fallback).
 */
process HIFIASM_META {
    tag { meta.id }
    label 'process_highmem'
    conda "${projectDir}/envs/assembly_hifi.yml"

    publishDir "${params.outdir}/02_assembly/hifiasm_meta", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(long_reads)

    output:
    tuple val(meta), path("${meta.id}.hifiasm.fasta"), emit: assembly
    tuple val(meta), path("${meta.id}.p_ctg.gfa"), emit: graph

    script:
    """
    hifiasm -t ${task.cpus} -o ${meta.id} ${long_reads}
    # Convert primary contig graph to FASTA
    awk '/^S/{printf ">%s\\n%s\\n", \$2, \$3}' ${meta.id}.p_ctg.gfa > ${meta.id}.hifiasm.fasta
    """
}
