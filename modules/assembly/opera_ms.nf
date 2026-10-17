/*
 * OPERA-MS hybrid metagenomic assembly (DAG node: assembly_opera_ms; default
 * hybrid assembler). OPERA-MS is not on bioconda and has no community
 * container; install OPERA-MS.pl manually and ensure it is on PATH.
 */
process OPERA_MS {
    tag { meta.id }
    label 'process_highmem'

    publishDir "${params.outdir}/02_assembly/opera_ms", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(read1), path(read2), path(long_reads)

    output:
    tuple val(meta), path("${meta.id}.opera_ms.contigs.fasta"), emit: assembly
    tuple val(meta), path("${meta.id}.opera_ms_out"), emit: output_dir

    script:
    """
    OPERA-MS.pl \\
        --short-read1 ${read1} --short-read2 ${read2} \\
        --long-read ${long_reads} \\
        --out-dir ${meta.id}.opera_ms_out \\
        --num-processors ${task.cpus}
    # Normalize the OPERA-MS final contigs
    if [ -f ${meta.id}.opera_ms_out/intermediate_files/opera_long_read/GF3/contigs.fa ]; then
        cp ${meta.id}.opera_ms_out/intermediate_files/opera_long_read/GF3/contigs.fa ${meta.id}.opera_ms.contigs.fasta
    elif [ -f ${meta.id}.opera_ms_out/contigs.fasta ]; then
        cp ${meta.id}.opera_ms_out/contigs.fasta ${meta.id}.opera_ms.contigs.fasta
    else
        find ${meta.id}.opera_ms_out -name 'contigs.fa*' | head -1 | xargs -I{} cp {} ${meta.id}.opera_ms.contigs.fasta
    fi
    """
}
