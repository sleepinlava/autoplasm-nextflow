process DASTOOL_DASTOOL {
    cache 'deep'
    tag "${meta.id}"
    label 'process_medium'

    conda "${moduleDir}/environment.yml"
    container "${workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container
        ? 'https://depot.galaxyproject.org/singularity/das_tool:1.1.7--r44hdfd78af_1'
        : 'quay.io/biocontainers/das_tool:1.1.7--r44hdfd78af_1'}"

    input:
    tuple val(meta), path(contigs), path(bins, arity: '1..*'), path(proteins)
    tuple path(db_directory, stageAs: 'dastool_db'), val(db_identity)

    output:
    tuple val(meta), path("*.log")                                      , emit: log
    tuple val(meta), path("*_summary.tsv")              , optional: true, emit: summary
    tuple val(meta), path("*_DASTool_contig2bin.tsv")   , optional: true, emit: contig2bin
    tuple val(meta), path("*.eval")                     , optional: true, emit: eval
    tuple val(meta), path("*_DASTool_bins/*.fa")        , optional: true, emit: bins
    tuple val(meta), path("*.pdf")                      , optional: true, emit: pdfs
    tuple val(meta), path("*.candidates.faa")           , optional: true, emit: candidates_faa
    tuple val(meta), path("*_proteins.faa")             , optional: true, emit: fasta_proteins
    tuple val(meta), path("*.archaea.scg")              , optional: true, emit: fasta_archaea_scg
    tuple val(meta), path("*.bacteria.scg")             , optional: true, emit: fasta_bacteria_scg
    tuple val(meta), path("*.b6")                       , optional: true, emit: b6
    tuple val(meta), path("*.seqlength")                , optional: true, emit: seqlength
    tuple val("${task.process}"), val('dastool'), eval('DAS_Tool --version 2>&1 | grep "DAS Tool" | sed "s/DAS Tool //"'), topic: versions, emit: versions_dastool
    tuple val("${task.process}"), val(meta), path("${meta.id}.DASTOOL_DASTOOL.task_command.sh"),
          val('DAS_Tool --version'), eval('DAS_Tool --version 2>&1 | sed -n "1p"'),
          eval("sha256sum '${meta.id}.DASTOOL_DASTOOL.task_command.sh'"), emit: task_provenance


    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    def bin_list = bins.join(",")
    // The upstream bash launcher and R-generated helper commands split paths
    // on whitespace. Use a fixed task-local name for the optional directory.
    def db_dir = db_directory ? '--dbDirectory dastool_db' : ''
    def check_db = db_directory ? '''
    if [ ! -d dastool_db ]; then
        echo 'DAS Tool custom database must be a directory' >&2
        exit 1
    fi
    for db_file in bac.all.faa bac.scg.faa bac.scg.lookup arc.all.faa arc.scg.faa arc.scg.lookup; do
        if [ ! -s "dastool_db/$db_file" ]; then
            echo "DAS Tool custom database is missing or empty: $db_file" >&2
            exit 1
        fi
    done
    ''' : ''
    def clean_contigs = contigs.toString() - ".gz"
    def decompress_contigs = contigs.toString() == clean_contigs ? "" : "gunzip -q -f ${contigs}"
    def clean_proteins = proteins ? proteins.toString() - ".gz" : ""
    def decompress_proteins = proteins && (proteins.toString() != clean_proteins) ? "gunzip -f ${proteins}" : ""
    def proteins_pred = proteins ? "-p ${clean_proteins}" : ""
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.DASTOOL_DASTOOL.task_command.sh'
    ${check_db}
    ${decompress_proteins}
    ${decompress_contigs}

    DAS_Tool \\
        ${args} \\
        ${proteins_pred} \\
        ${db_dir} \\
        -t ${task.cpus} \\
        -i ${bin_list} \\
        -c ${clean_contigs} \\
        -o ${prefix}
    """

    stub:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.DASTOOL_DASTOOL.task_command.sh'
    touch ${prefix}_DASTool.log
    touch ${prefix}_DASTool_summary.tsv
    touch ${prefix}_DASTool_contig2bin.tsv
    touch ${prefix}_allBins.eval
    touch ${prefix}_proteins.faa.scg.candidates.faa
    touch ${prefix}_proteins.faa
    touch ${prefix}_proteins.faa.archaea.scg
    touch ${prefix}_proteins.faa.bacteria.scg
    touch ${prefix}_proteins.faa.findSCG.b6
    touch ${prefix}.seqlength
    mkdir ${prefix}_DASTool_bins
    touch ${prefix}_DASTool_bins/${prefix}.1.fa
    """
}
