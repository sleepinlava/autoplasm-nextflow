process SPADES {
    cache 'deep'
    tag "$meta.id"
    label 'process_high'

    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container ?
        'https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/7b/7b7b68c7f8471d9111841dbe594c00a41cdd3b713015c838c4b22705cfbbdfb2/data' :
        'community.wave.seqera.io/library/spades:4.1.0--77799c52e1d1054a' }"

    input:
    tuple val(meta), path(illumina), path(pacbio), path(nanopore)
    path yml
    path hmm
    // Explicit regular files: helper changes participate in deep caching.
    path(autoplasm_helper_0, stageAs: '.spades_graph_provenance.py')

    output:
    tuple val(meta), path('*.scaffolds.fa.gz')    , optional:true, emit: scaffolds
    tuple val(meta), path('*.contigs.fa.gz')      , optional:true, emit: contigs
    tuple val(meta), path('*.transcripts.fa.gz')  , optional:true, emit: transcripts
    tuple val(meta), path('*.gene_clusters.fa.gz'), optional:true, emit: gene_clusters
    tuple val(meta), path('*.assembly.gfa.gz')    , optional:true, emit: gfa
    // Local patch (refactor/nf-core-modules): also export SPAdes'
    // assembly_graph.fastg. The pipeline's Recycler plasmid binning
    // consumes the FASTG graph (upstream only exports the GFA sibling).
    tuple val(meta), path('*.assembly_graph.fastg'), optional:true, emit: fastg
    // Local interface: graph and k provenance come from this same successful task.
    tuple val(meta), path('*.assembly_graph.fastg'), path('*.graph_provenance.json'), optional:true, emit: recycler_graph
    // gplas consumes GFA segments, not assembled contigs or FASTG records.
    tuple val(meta), path('*.gplas.gfa'), optional:true, emit: gplas_graph
    tuple val(meta), path('*.plasmaag_spades', type: 'dir'), optional:true, emit: plasmaag_assembly
    tuple val(meta), path('*.warnings.log')         , optional:true, emit: warnings
    tuple val(meta), path('*.spades.log')         , emit: log
    tuple val("${task.process}"), val('spades'), eval("spades.py --version 2>&1 | sed -n 's/^.*SPAdes genome assembler v//p'"), topic: versions, emit: versions_spades
    tuple val("${task.process}"), val(meta), path("${prefix}.SPADES.task_command.sh"),
          val('spades.py --version'), eval('spades.py --version'),
          eval("sha256sum '${prefix}.SPADES.task_command.sh'"), emit: task_provenance

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    prefix = task.ext.prefix ?: "${meta.id}"
    def maxmem = task.memory.toGiga()
    def illumina_reads = illumina ? ( meta.single_end ? "-s $illumina" : "-1 ${illumina[0]} -2 ${illumina[1]}" ) : ""
    def pacbio_reads = pacbio ? "--pacbio $pacbio" : ""
    def nanopore_reads = nanopore ? "--nanopore $nanopore" : ""
    def custom_hmms = hmm ? "--custom-hmms $hmm" : ""
    def reads = yml ? "--dataset $yml" : "$illumina_reads $pacbio_reads $nanopore_reads"
    def export_plasmaag = task.ext.plasmaag ?: false
    // The provenance helper is an explicit deeply hashed file input.
    """
    cp -- "\${BASH_SOURCE[0]}" '${prefix}.SPADES.task_command.sh'
    spades.py \\
        $args \\
        --threads $task.cpus \\
        --memory $maxmem \\
        $custom_hmms \\
        $reads \\
        -o ./
    mv spades.log ${prefix}.spades.log

    if ${export_plasmaag}; then
        mkdir ${prefix}.plasmaag_spades
        cp contigs.fasta contigs.paths assembly_graph_after_simplification.gfa ${prefix}.plasmaag_spades/
    fi
    if [ -f scaffolds.fasta ]; then
        mv scaffolds.fasta ${prefix}.scaffolds.fa
        gzip -n ${prefix}.scaffolds.fa
    fi
    if [ -f contigs.fasta ]; then
        mv contigs.fasta ${prefix}.contigs.fa
        gzip -n ${prefix}.contigs.fa
    fi
    if [ -f transcripts.fasta ]; then
        mv transcripts.fasta ${prefix}.transcripts.fa
        gzip -n ${prefix}.transcripts.fa
    fi
    if [ -f assembly_graph_with_scaffolds.gfa ]; then
        mv assembly_graph_with_scaffolds.gfa ${prefix}.assembly.gfa
        gzip -n ${prefix}.assembly.gfa
    fi

    # Local patch (refactor/nf-core-modules): keep the FASTG graph for Recycler and graph consumers.
    if [ -f assembly_graph.fastg ]; then
        cp assembly_graph.fastg ${prefix}.assembly_graph.fastg
        python3 .spades_graph_provenance.py --assembly-dir . \\
            --graph ${prefix}.assembly_graph.fastg --log ${prefix}.spades.log \\
            --out ${prefix}.graph_provenance.json
    fi

    if [ -f assembly_graph_after_simplification.gfa ]; then
        cp assembly_graph_after_simplification.gfa ${prefix}.gplas.gfa
    fi

    if [ -f gene_clusters.fasta ]; then
        mv gene_clusters.fasta ${prefix}.gene_clusters.fa
        gzip -n ${prefix}.gene_clusters.fa
    fi

    if [ -f warnings.log ]; then
        mv warnings.log ${prefix}.warnings.log
    fi
    """

    stub:
    prefix = task.ext.prefix ?: "${meta.id}"
    """
    cp -- "\${BASH_SOURCE[0]}" '${prefix}.SPADES.task_command.sh'
    echo "" | gzip > ${prefix}.scaffolds.fa.gz
    echo "" | gzip > ${prefix}.contigs.fa.gz
    echo "" | gzip > ${prefix}.transcripts.fa.gz
    echo "" | gzip > ${prefix}.gene_clusters.fa.gz
    echo "" | gzip > ${prefix}.assembly.gfa.gz
    touch ${prefix}.assembly_graph.fastg
    touch ${prefix}.gplas.gfa
    echo '{"stub":true}' > ${prefix}.graph_provenance.json
    touch ${prefix}.spades.log
    touch ${prefix}.warnings.log
    """
}
