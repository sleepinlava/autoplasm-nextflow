/*
 * OPERA-MS hybrid metagenomic assembly (pipeline step: assembly_opera_ms;
 * default hybrid assembler). OPERA-MS is not on bioconda and has no community
 * container; install OPERA-MS.pl manually and ensure it is on PATH.
 */
process OPERA_MS {
    cache 'deep'
    tag { meta.id }
    label 'process_highmem'

    publishDir "${params.outdir}/02_assembly/opera_ms", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(read1), path(read2), path(long_reads)
    // Explicit regular files: helper changes participate in deep caching.
    path(autoplasm_helper_0, stageAs: 'validate_opera_ms_output.py')

    output:
    tuple val(meta), path("${meta.id}.opera_ms.contigs.fasta"), emit: assembly
    tuple val(meta), path("${meta.id}.opera_ms_out"), emit: output_dir
    tuple val("${task.process}"), val(meta), path("${meta.id}.OPERA_MS.task_command.sh"),
          val('perl -S OPERA-MS.pl --help'), eval("perl -S OPERA-MS.pl --help 2>&1 | sed -n '1p'"),
          eval("sha256sum '${meta.id}.OPERA_MS.task_command.sh'"), emit: task_provenance

    script:
    def shellQuote = { value -> "'" + value.toString().replace("'", "'\"'\"'") + "'" }
    // v0.8.3 check_data rejects gzip long reads. Keep the staged source intact
    // and decode to a private file before invoking the real assembler.
    def compressed = long_reads.name.toLowerCase().endsWith('.gz')
    def input_long_reads = compressed ? "opera_ms_inputs/${long_reads.name.substring(0, long_reads.name.length() - 3)}" : long_reads
    def decode = compressed ? "mkdir -p opera_ms_inputs\ngzip -cd -- ${shellQuote.call(long_reads)} > ${shellQuote.call(input_long_reads)}" : ''
    // Upstream v0.8.3 ships OPERA-MS.pl without a shebang (first line is a
    // comment), so invoke it through perl explicitly and search PATH (-S).
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.OPERA_MS.task_command.sh'
    ${decode}
    perl -S OPERA-MS.pl \\
        --short-read1 ${read1} --short-read2 ${read2} \\
        --long-read ${shellQuote.call(input_long_reads)} \\
        --out-dir ${meta.id}.opera_ms_out \\
        --num-processors ${task.cpus}
    # v0.8.3 write_final_assembly writes this exact final product.
    if [ ! -s ${meta.id}.opera_ms_out/contigs.fasta ]; then
        echo 'OPERA-MS final assembly missing or empty: ${meta.id}.opera_ms_out/contigs.fasta' >&2
        exit 1
    fi
    python3 validate_opera_ms_output.py --output-dir ${meta.id}.opera_ms_out
    cp ${meta.id}.opera_ms_out/contigs.fasta ${meta.id}.opera_ms.contigs.fasta
    """
}
