/*
 * PlasmidHostFinder assembly-based host prediction (DAG node:
 * host_prediction_plasmidhostfinder; assembly platform).
 */
process PLASMIDHOSTFINDER {
    tag { meta.id }
    label 'process_low'
    conda "${projectDir}/envs/plasmidhostfinder.yml"

    publishDir "${params.outdir}/07_host_prediction/${meta.id}/plasmidhostfinder", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(plasmid_contigs)
    path phf_db

    output:
    tuple val(meta), path("${meta.id}.plasmidhostfinder.tsv"), emit: predictions

    script:
    """
    plasmidhostfinder.py -i ${plasmid_contigs} -o . -l genus -t 0.3 -p ${phf_db}
    find . -maxdepth 2 -name '*.tsv' ! -name '${meta.id}.plasmidhostfinder.tsv' \\
        | head -1 | xargs -I{} cp {} ${meta.id}.plasmidhostfinder.tsv
    """
}
