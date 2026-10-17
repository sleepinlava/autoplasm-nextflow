process HIFIADAPTERFILT_HIFIADAPTERFILT {
    tag "$meta.id"
    label 'process_medium'

    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/hifiadapterfilt:3.0.0--hdfd78af_0':
        'quay.io/biocontainers/hifiadapterfilt:3.0.0--hdfd78af_0' }"

    input:
    tuple val(meta), path(reads), path(db)

    output:
    tuple val(meta), path("${prefix}.filt.fastq.gz")       , emit: fastq
    tuple val(meta), path("${prefix}.stats")               , emit: stats
    tuple val(meta), path("${prefix}.contaminant.blastout"), emit: blastout
    tuple val(meta), path("${prefix}.blocklist")           , emit: blocklist
    tuple val("${task.process}"), val('hifiadapterfilt'), eval("hifiadapterfilt.sh --version 2>&1 | head -1"), topic: versions, emit: versions_hifiadapterfilt

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def ext  = reads.name.endsWith('.bam') ? '.bam' :
        (reads.name.endsWith('.fastq.gz') || reads.name.endsWith('.fq.gz')) ? '.fastq.gz' : '.fastq'
    prefix   = task.ext.prefix ?: "${meta.id}"
    // Local patch (refactor/nf-core-modules): the db input may be empty. In
    // that case fall back to the adapter database shipped inside the tool's
    // own package (bioconda: $CONDA_PREFIX/bin/DB; biocontainer:
    // /usr/local/bin/DB), which sits next to the hifiadapterfilt.sh binary.
    def db_link = db
        ? "ln -s \$(realpath ${db}) HiFiAdapterFilt/DB"
        : "ln -s \$(dirname \$(command -v hifiadapterfilt.sh))/DB HiFiAdapterFilt/DB"
    """
    # Workaround: BusyBox sed in this container lacks GNU step-address syntax (1~4,2~4).
    # hifiadapterfilt.sh uses `sed -n '1~4s/^@/>/p;2~4p'` to convert FASTQ→FASTA for
    # BLAST, but BusyBox sed silently produces empty output, preventing adapter detection.
    # An awk-based sed wrapper is placed earlier in PATH to intercept step-address calls;
    # all other sed invocations fall through to /usr/bin/sed.
    mkdir -p _wrappers
    cat > _wrappers/sed << 'SEDWRAP'
#!/bin/sh
case "\$*" in
    *1~4*)
        awk 'NR%4==1{print ">"substr(\$0,2)} NR%4==2{print}'
        ;;
    *)
        /usr/bin/sed "\$@"
        ;;
esac
SEDWRAP
    chmod +x _wrappers/sed

    # Workaround: hifiadapterfilt.sh resolves the BLAST database path by splitting PATH
    # on ':' and grep-ing for "HiFiAdapterFilt/DB". The bioconda package installs the
    # database to /usr/local/bin/DB which never matches that pattern. Create the expected
    # directory structure from the provided db input and inject it into PATH.
    mkdir -p HiFiAdapterFilt
    ${db_link}
    export PATH="\$PWD/_wrappers:\$PWD/HiFiAdapterFilt/DB:\$PATH"

    ln -s \$(realpath ${reads}) ${prefix}${ext}

    hifiadapterfilt.sh \\
        -t ${task.cpus} \\
        -o . \\
        ${args}
    """

    stub:
    prefix = task.ext.prefix ?: "${meta.id}"
    """
    echo "" | gzip > ${prefix}.filt.fastq.gz
    touch ${prefix}.stats
    touch ${prefix}.contaminant.blastout
    touch ${prefix}.blocklist
    """
}
