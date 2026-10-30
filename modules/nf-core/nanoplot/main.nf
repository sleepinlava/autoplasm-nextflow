process NANOPLOT {
    tag "$meta.id"
    label 'process_low'

    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/nanoplot:1.47.0--pyhdfd78af_0' :
        'quay.io/biocontainers/nanoplot:1.47.0--pyhdfd78af_0' }"

    input:
    tuple val(meta), path(ontfile)

    output:
    tuple val(meta), path("*.html")                , emit: html
    tuple val(meta), path("*.png") , optional: true, emit: png
    tuple val(meta), path("*.txt")                 , emit: txt
    tuple val("${task.process}"), val('NanoPlot'), eval('NanoPlot --version | sed \'s/^.*NanoPlot //; s/ .*\$//\''), emit: versions_nanoplot, topic: versions
    tuple val("${task.process}"), val(meta), path("${meta.id}.NANOPLOT.task_command.sh"),
          val('NanoPlot --version'), eval('NanoPlot --version'),
          eval("sha256sum '${meta.id}.NANOPLOT.task_command.sh'"), emit: task_provenance

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    // Local patch (refactor/nf-core-modules): accept plain .fastq/.fq too.
    // The pipeline's Dorado basecaller emits uncompressed '<id>.dorado.fastq',
    // which upstream's gz/txt-only sniffing would silently drop.
    def input_file = ("$ontfile".endsWith(".fastq.gz") || "$ontfile".endsWith(".fq.gz")) ? "--fastq ${ontfile}" :
        ("$ontfile".endsWith(".fastq") || "$ontfile".endsWith(".fq")) ? "--fastq ${ontfile}" :
        ("$ontfile".endsWith(".txt")) ? "--summary ${ontfile}" : ''
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.NANOPLOT.task_command.sh'
    NanoPlot \\
        $args \\
        -t $task.cpus \\
        $input_file
    """

    stub:
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.NANOPLOT.task_command.sh'
    touch LengthvsQualityScatterPlot_dot.html
    touch LengthvsQualityScatterPlot_kde.html
    touch NanoPlot-report.html
    touch NanoStats.txt
    touch Non_weightedHistogramReadlength.html
    touch Non_weightedLogTransformed_HistogramReadlength.html
    touch WeightedHistogramReadlength.html
    touch WeightedLogTransformed_HistogramReadlength.html
    touch Yield_By_Length.html
    """
}
