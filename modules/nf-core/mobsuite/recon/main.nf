include { mobsuiteQuote } from '../../../../lib/mobsuite_runtime'

process MOBSUITE_RECON {
    cache 'deep'
    tag "$meta.id"
    label 'process_medium'

    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/mob_suite:3.1.9--pyhdfd78af_0':
        'quay.io/biocontainers/mob_suite:3.1.9--pyhdfd78af_0' }"

    input:
    tuple val(meta), path(fasta)
    path(preflight_helper, stageAs: 'mobsuite_preflight.py')

    output:
    tuple val(meta), path("results/chromosome.fasta")    , emit: chromosome
    tuple val(meta), path("results/contig_report.txt")   , emit: contig_report
    tuple val(meta), path("results/plasmid_*.fasta")     , emit: plasmids        , optional: true
    tuple val(meta), path("results/mobtyper_results.txt"), emit: mobtyper_results, optional: true
    tuple val("${task.process}"), val('mobsuite'), eval("mob_recon --version 2>&1 | sed 's/.*mob_recon //; s/ .*//'"), emit: versions_mobsuite, topic: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    def is_compressed = fasta.getName().endsWith(".gz") ? true : false
    def fasta_name = fasta.getName().replace(".gz", "")
    """
    if [ "${is_compressed}" == "true" ]; then
        gzip -c -d ${mobsuiteQuote(fasta)} > ${mobsuiteQuote(fasta_name)}
    fi

    python3 mobsuite_preflight.py --tool mob_recon --output mobsuite_preflight.json --execute -- \\
        --infile ${mobsuiteQuote(fasta_name)} \\
        ${args} \\
        --num_threads ${task.cpus} \\
        --outdir results \\
        --sample_id ${mobsuiteQuote(prefix)}
    """

    stub:
    """
    mkdir -p results

    touch results/chromosome.fasta
    touch results/contig_report.txt
    """
}
