/*
 * OPERA-MS hybrid metagenomic assembly (DAG node: assembly_opera_ms; default
 * hybrid assembler). OPERA-MS is not on bioconda; install OPERA-MS.pl manually
 * and ensure it is on PATH.
 */
process OPERA_MS {
    tag { meta.id }
    label 'process_highmem'

    publishDir "${params.outdir}/02_assembly/${meta.id}", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(read1), path(read2), path(long_reads)

    output:
    tuple val(meta), path("contigs.fasta"), emit: assembly
    tuple val(meta), path("opera_ms_out"), emit: output_dir

    script:
    """
    OPERA-MS.pl \\
        --short-read1 ${read1} --short-read2 ${read2} \\
        --long-read ${long_reads} \\
        --out-dir opera_ms_out \\
        --num-processors ${task.cpus}
    # Normalize the OPERA-MS final contigs to contigs.fasta
    if [ -f opera_ms_out/intermediate_files/opera_long_read/GF3/contigs.fa ]; then
        cp opera_ms_out/intermediate_files/opera_long_read/GF3/contigs.fa contigs.fasta
    elif [ -f opera_ms_out/contigs.fasta ]; then
        cp opera_ms_out/contigs.fasta contigs.fasta
    else
        find opera_ms_out -name 'contigs.fa*' | head -1 | xargs -I{} cp {} contigs.fasta
    fi
    """
}
