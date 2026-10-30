/*
 * hifiasm-meta HiFi metagenomic assembly (pipeline step: assembly_hifiasm).
 * Use the dedicated hifiasm_meta binary and its primary contig graph.
 * hifiasm_meta ships as a bioconda package (envs/assembly_hifi.yml) but has
 * no quay.io/biocontainers/hifiasm-meta image (verified 2026-10-16), so this
 * process stays conda-only on purpose.
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
    tuple val("${task.process}"), val(meta), path("${meta.id}.HIFIASM_META.task_command.sh"),
          val('hifiasm_meta --version'), eval('hifiasm_meta --version'),
          eval("sha256sum '${meta.id}.HIFIASM_META.task_command.sh'"), emit: task_provenance

    script:
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.HIFIASM_META.task_command.sh'
    hifiasm_meta -t ${task.cpus} -o ${meta.id} ${long_reads}
    # Convert primary contig graph to FASTA
    awk '/^S/{printf ">%s\\n%s\\n", \$2, \$3}' ${meta.id}.p_ctg.gfa > ${meta.id}.hifiasm.fasta
    """
}
