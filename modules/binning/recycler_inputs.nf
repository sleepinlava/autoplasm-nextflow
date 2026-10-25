/* Dedicated graph-node mapping; contig coverage BAMs are not Recycler inputs.
 * BWA preparation follows Recycler 0.7's documented recipe. Its independently
 * pinned nf-core BWA stack is recorded in docs/tool-audit/evidence/.
 */
process RECYCLER_REFERENCE {
    cache 'deep'
    tag { meta.id }
    label 'process_low'
    conda "${moduleDir}/../../envs/recycler.yml"
    container 'quay.io/biocontainers/recycler:0.7--py_3'

    input:
    tuple val(meta), path(graph), path(provenance), path(read1), path(read2)
    // Explicit regular files: helper changes participate in deep caching.
    tuple path(autoplasm_helper_0, stageAs: 'validate_recycler_inputs.py'), path(autoplasm_helper_1, stageAs: 'recycler_graph_reference.py')

    output:
    tuple val(meta), path(graph), path(provenance), path("${meta.id}.graph_nodes.fasta"), path(read1), path(read2), emit: reference

    script:
    """
    python recycler_graph_reference.py --graph "${graph}" --provenance "${provenance}" \\
        --out ${meta.id}.graph_nodes.fasta
    """
}

process RECYCLER_ALIGN {
    tag { meta.id }
    label 'process_medium'
    conda "${moduleDir}/recycler_align.yml"
    container 'community.wave.seqera.io/library/bwa_htslib_samtools:83b50ff84ead50d0'

    input:
    tuple val(meta), path(graph), path(provenance), path(reference), path(read1), path(read2)

    output:
    tuple val(meta), path(graph), path(provenance), path("${meta.id}.graph_nodes.bam"), path("${meta.id}.graph_nodes.bam.bai"), emit: bam

    script:
    """
    set -o pipefail
    bwa index "${reference}"
    bwa mem -t ${task.cpus} "${reference}" "${read1}" "${read2}" \\
        | samtools view -b -F 0x0800 - \\
        | samtools sort -@ ${task.cpus} -o ${meta.id}.graph_nodes.bam -
    samtools index ${meta.id}.graph_nodes.bam
    """
}

workflow RECYCLER_INPUTS {
    take:
    graph_reads // one keyed tuple(meta, FASTG, provenance, original read1, read2)

    main:
    RECYCLER_REFERENCE(graph_reads, Channel.value(tuple(file("${moduleDir}/../../bin/validate_recycler_inputs.py", checkIfExists: true), file("${moduleDir}/../../bin/recycler_graph_reference.py", checkIfExists: true))))
    RECYCLER_ALIGN(RECYCLER_REFERENCE.out.reference)

    emit:
    bam = RECYCLER_ALIGN.out.bam
}
