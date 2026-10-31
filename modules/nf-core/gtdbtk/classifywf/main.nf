process GTDBTK_CLASSIFYWF {
    cache 'deep'
    tag "${meta.id}"
    label 'process_high_memory'

    conda "${moduleDir}/environment.yml"
    container "${workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container
        ? 'https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/fa/fa734cc7e63b0f7d0c04788ec61de5e6a101a07e966d3dde24384d54a9d75e85/data'
        : 'community.wave.seqera.io/library/gtdbtk:2.7.2--64b0fd171db01270'}"

    input:
    tuple val(meta)   , path("bins/*")
    tuple val(db_name), path(db), val(db_identity)
    val use_pplacer_scratch_dir
    // Explicit regular files: helper changes participate in deep caching.
    path(autoplasm_helper_0, stageAs: 'normalize_gtdb_bins.py')

    output:
    tuple val('gtdbtk_db'), val(db_identity), emit: database_identity
    tuple val(meta), path("${prefix}")                               , emit: gtdb_outdir
    tuple val(meta), path("${prefix}/classify/*.summary.tsv")        , emit: summary
    tuple val(meta), path("${prefix}/classify/*.classify.tree")      , emit: tree       , optional: true
    tuple val(meta), path("${prefix}/identify/*.markers_summary.tsv"), emit: markers    , optional: true
    tuple val(meta), path("${prefix}/align/*.msa.fasta.gz")          , emit: msa        , optional: true
    tuple val(meta), path("${prefix}/align/*.user_msa.fasta.gz")     , emit: user_msa   , optional: true
    tuple val(meta), path("${prefix}/align/*.filtered.tsv")          , emit: filtered   , optional: true
    tuple val(meta), path("${prefix}/identify/*.failed_genomes.tsv") , emit: failed     , optional: true
    tuple val(meta), path("${prefix}/${prefix}.log")                 , emit: log
    tuple val(meta), path("${prefix}/${prefix}.warnings.log")        , emit: warnings
    tuple val(meta), path("${prefix}.genome_inputs.json")            , emit: genome_inputs
    tuple val("${task.process}"), val('gtdbtk'), eval("gtdbtk --version 2>&1 | grep -Eo '[0-9]+(\\.[0-9]+)+' | head -1") , topic: versions, emit: versions_gtdbtk
    tuple val("${task.process}"), val('gtdb_db'), eval('grep VERSION_DATA \$GTDBTK_DATA_PATH/metadata/metadata.txt | sed "s/VERSION_DATA=//"'), topic: versions, emit: versions_gtdbtk_db
    tuple val("${task.process}"), val(meta), path("${meta.id}.GTDBTK_CLASSIFYWF.task_command.sh"),
          val('gtdbtk --version'), eval('gtdbtk --version'),
          eval("sha256sum '${meta.id}.GTDBTK_CLASSIFYWF.task_command.sh'"), emit: task_provenance


    when:
    task.ext.when == null || task.ext.when

    script:
    def args            = task.ext.args ?: ''
    prefix              = task.ext.prefix ?: "${meta.id}"
    def pplacer_scratch = use_pplacer_scratch_dir ? "--scratch_dir pplacer_tmp" : ""
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.GTDBTK_CLASSIFYWF.task_command.sh'
    export GTDBTK_DATA_PATH="\$(find -L ${db} -name 'metadata' -type d -exec dirname {} \\;)"

    python3 normalize_gtdb_bins.py \\
        --input-dir bins \\
        --output-dir gtdbtk_input \\
        --manifest "${prefix}.genome_inputs.json"

    if [ "${pplacer_scratch}" != "" ] ; then
        mkdir pplacer_tmp
    fi

    gtdbtk classify_wf \\
        ${args} \\
        --genome_dir gtdbtk_input \\
        --extension fna \\
        --prefix "${prefix}" \\
        --out_dir ${prefix} \\
        --cpus ${task.cpus} \\
        ${pplacer_scratch}

    mv ${prefix}/gtdbtk.log "${prefix}/${prefix}.log"
    mv ${prefix}/gtdbtk.warnings.log "${prefix}/${prefix}.warnings.log"
    """

    stub:
    prefix = task.ext.prefix ?: "${meta.id}"
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.GTDBTK_CLASSIFYWF.task_command.sh'
    export GTDBTK_DATA_PATH="\$(find -L ${db} -name 'metadata' -type d -exec dirname {} \\;)"

    mkdir ${prefix}
    mkdir ${prefix}/identify
    mkdir ${prefix}/classify
    mkdir ${prefix}/align

    touch ${prefix}/classify/${prefix}.ar53.summary.tsv
    touch ${prefix}/classify/${prefix}.bac120.summary.tsv
    touch ${prefix}/classify/${prefix}.ar53.classify.tree
    touch ${prefix}/classify/${prefix}.bac120.classify.tree

    touch ${prefix}/identify/${prefix}.ar53.markers_summary.tsv
    touch ${prefix}/identify/${prefix}.bac120.markers_summary.tsv

    echo "" | gzip > ${prefix}/align/${prefix}.ar53.msa.fasta.gz
    echo "" | gzip > ${prefix}/align/${prefix}.bac120.user_msa.fasta.gz
    touch ${prefix}/align/${prefix}.ar53.filtered.tsv
    touch ${prefix}/align/${prefix}.bac120.filtered.tsv

    touch ${prefix}/${prefix}.log
    touch ${prefix}/${prefix}.warnings.log
    touch ${prefix}/${prefix}.failed_genomes.tsv
    echo '{"status":"stub_not_validated"}' > "${prefix}.genome_inputs.json"
    """
}
