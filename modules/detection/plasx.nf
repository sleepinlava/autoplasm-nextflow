/*
 * PlasX plasmid classification (DAG node: plasmid_detect_plasx; optional).
 * Requires the PlasX annotation and model files.
 */
process PLASX {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/plasx.yml"
    // PlasX 无 bioconda 包（envs pin 亦无法解析），container 用 python 运行时兜底
    // （脚本另需 prodigal，container 兜底不包含，conda 仍是唯一完整路径）
    container 'quay.io/biocontainers/python:3.11'

    publishDir "${params.outdir}/04_plasmid_detection/plasx", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly)
    path plasx_annotations
    path plasx_model

    output:
    tuple val(meta), path("${meta.id}.plasx.tsv"), emit: predictions

    script:
    """
    # PlasX needs de-novo gene calls; prodigal meta mode provides them
    # (simplification of the ABI anvi'o-based gene-calls input).
    prodigal -i ${assembly} -o ${meta.id}.gff -a ${meta.id}.faa -d ${meta.id}.ffn -p meta
    plasx predict \\
        -a ${plasx_annotations} \\
        -g ${meta.id}.gff \\
        -m ${plasx_model} \\
        -o ${meta.id}.plasx.tsv \\
        --overwrite
    """
}
