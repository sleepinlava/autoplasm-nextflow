process MOSTPLAS {
    label 'process_medium'
    cache 'deep'
    conda "${projectDir}/envs/mostplas.yml"
    publishDir "${params.outdir}/07_host_prediction/mostplas", mode: params.publish_dir_mode
    input:
    path catalogue
    path complete_ids
    path source, stageAs:'mostplas_source'
    path code_assets,stageAs:'source_assets/*'
    output:
    path("*.task_command.sh"), emit: commands
    path('mostplas'), emit: predictions
    script:
    """
    cp -- "\${BASH_SOURCE[0]}" "${task.process.tokenize(':').last()}.task_command.sh"
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    export PYTHONPATH=\$PWD/analysis_code
    python3 analysis_code/mostplas_predict.py --source '${source}' --catalogue '${catalogue}' --complete-ids '${complete_ids}' \\
        --output mostplas --threshold ${params.mostplas_threshold}
    """
}
process PLSDB_SEARCH {
    label 'process_medium'
    cache 'deep'
    conda "${projectDir}/modules/nf-core/blast/blastn/environment.yml"
    container 'community.wave.seqera.io/library/blast:2.17.0--d4fb881691596759'
    publishDir "${params.outdir}/07_host_prediction/plsdb", mode: params.publish_dir_mode
    input:
    path catalogue
    path reference
    path hosts
    path code_assets,stageAs:'source_assets/*'
    output:
    path("*.task_command.sh"), emit: commands
    path('plsdb'), emit: predictions
    script:
    """
    cp -- "\${BASH_SOURCE[0]}" "${task.process.tokenize(':').last()}.task_command.sh"
    mkdir -p analysis_code
    cp -L source_assets/* analysis_code/
    export PYTHONPATH=\$PWD/analysis_code
    mkdir plsdb
    touch plsdb/alignments.tsv
    if [ -s '${catalogue}/plasmids.fasta' ]; then
        blastn -task megablast -query '${catalogue}/plasmids.fasta' -subject '${reference}' \\
          -outfmt '6 qseqid sseqid pident length qstart qend sstart send qlen slen evalue bitscore' \\
          -num_threads ${task.cpus} -max_target_seqs 100 -out plsdb/alignments.tsv
    fi
    python3 analysis_code/protocol_hosts.py plsdb --alignments plsdb/alignments.tsv --hosts '${hosts}' --output plsdb/host_evidence.tsv \\
        --identity ${params.plsdb_identity} --coverage ${params.plsdb_coverage}
    sha256sum '${reference}' '${hosts}' > plsdb/reference.sha256
    blastn -version > plsdb/version.txt
    """
}
