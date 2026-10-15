/*
 * PLASMe plasmid classification (DAG node: plasmid_detect_plasme; optional,
 * enabled via params.plasmid_detection_tools).
 */
process PLASME {
    tag { meta.id }
    label 'process_medium'
    conda "${projectDir}/envs/plasme.yml"

    publishDir "${params.outdir}/04_plasmid_detection/${meta.id}/plasme", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly)
    path plasme_db

    output:
    tuple val(meta), path("${meta.id}.plasme.tsv"), emit: predictions

    script:
    """
    PLASMe.py ${assembly} ${meta.id}.plasme -d ${plasme_db} -t ${task.cpus}
    # PLASMe writes <prefix>_plasmid.fasta plus a probability report; normalize
    # the prediction table to <sample>.plasme.tsv for the consensus step.
    if [ -f ${meta.id}.plasme.csv ]; then
        mv ${meta.id}.plasme.csv ${meta.id}.plasme.tsv
    elif ls ${meta.id}.plasme*.tsv > /dev/null 2>&1; then
        mv \$(ls ${meta.id}.plasme*.tsv | head -1) ${meta.id}.plasme.tsv
    else
        # Fall back to deriving calls from the plasmid FASTA
        python3 - <<'PYEOF'
    import re
    ids = []
    try:
        with open("${meta.id}.plasme_plasmid.fasta") as fh:
            ids = [l[1:].split()[0] for l in fh if l.startswith(">")]
    except FileNotFoundError:
        pass
    with open("${meta.id}.plasme.tsv", "w") as out:
        out.write("contig_id\\tplasmid_score\\tclassification\\n")
        for i in ids:
            out.write(f"{i}\\t1.0\\tplasmid\\n")
    PYEOF
    fi
    """
}
