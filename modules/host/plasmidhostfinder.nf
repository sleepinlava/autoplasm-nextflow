/*
    cache 'deep'
 * PlasmidHostFinder assembly-based host prediction (pipeline step:
 * host_prediction_plasmidhostfinder; assembly platform).
 */
process PLASMIDHOSTFINDER {
    tag { meta.id }
    label 'process_low'
    conda "${projectDir}/envs/plasmidhostfinder.yml"
    container 'quay.io/biocontainers/plasmidhostfinder:0.1.0--pyhdfd78af_0'

    publishDir "${params.outdir}/07_host_prediction/plasmidhostfinder", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)
    tuple path(phf_db), val(db_identity)

    output:
    tuple val(meta), path("${meta.id}.plasmidhostfinder.tsv"), emit: predictions
    tuple val("${task.process}"), val(meta), path("${meta.id}.PLASMIDHOSTFINDER.task_command.sh"),
          val('plasmidhostfinder --version'), eval('plasmidhostfinder --version'),
          eval("sha256sum '${meta.id}.PLASMIDHOSTFINDER.task_command.sh'"), emit: task_provenance


    script:
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.PLASMIDHOSTFINDER.task_command.sh'
    plasmidhostfinder.py -i ${plasmid_contigs} -o . -l genus -t 0.3 -p ${phf_db}
    find . -maxdepth 2 -name '*.tsv' ! -name '${meta.id}.plasmidhostfinder.tsv' \\
        | head -1 | xargs -I{} cp {} ${meta.id}.plasmidhostfinder.tsv
    """
}
