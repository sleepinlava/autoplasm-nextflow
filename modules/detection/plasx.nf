/* Full per-sample anvi'o COG14/Pfam32 and native PlasX de novo/model method. */
process PLASX_ANNOTATE {
    tag { meta.id }
    label 'process_medium'
    cache 'deep'
    conda "${moduleDir}/../../envs/plasx-anvio-linux-64.lock"
    publishDir "${params.outdir}/04_plasmid_detection/plasx", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly, stageAs: 'assembly_input/*')
    tuple path(anvio_source, stageAs: 'anvio_source'), val(anvio_source_identity)
    tuple path(cog_db, stageAs: 'cog_database'), val(cog_identity)
    tuple path(pfam_db, stageAs: 'pfam_database'), val(pfam_identity)
    // Explicit regular files: helper changes participate in deep caching.
    tuple path(autoplasm_helper_0, stageAs: 'plasx_inputs.py'), path(autoplasm_helper_1, stageAs: 'anvio_checked.py')

    output:
    tuple val(meta), path("${meta.id}.contigs.fasta"), path("${meta.id}.id_map.tsv"), path("${meta.id}.gene_calls.tsv"), path("${meta.id}.cogs_pfams.tsv"), emit: annotations
    tuple val(meta), path("${meta.id}.contigs.db"), emit: contigs_db
    tuple val(meta), path("${meta.id}.anvio_*.json"), emit: runtime
    tuple val("${task.process}"), val(meta), path("${meta.id}.PLASX_ANNOTATE.task_command.sh"),
          val('python3 anvio_checked.py -h'), eval('python3 anvio_checked.py -h'),
          eval("sha256sum '${meta.id}.PLASX_ANNOTATE.task_command.sh'"), emit: task_provenance

    script:
    def q = { value -> "'" + value.toString().replace("'", "'\"'\"'") + "'" }
    def p = meta.id.toString()
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.PLASX_ANNOTATE.task_command.sh'
    export PYTHONDONTWRITEBYTECODE=1
    export MPLCONFIGDIR="\$PWD/matplotlib"
    python3 plasx_inputs.py resources --cog-db cog_database --pfam-db pfam_database --record ${q.call(p + '.anvio_resources.json')}
    python3 plasx_inputs.py prepare --assembly ${q.call(assembly)} --sample ${q.call(p)} --prefix ${q.call(p)} --record ${q.call(p + '.anvio_input.json')}
    python3 anvio_checked.py --source anvio_source --record ${q.call(p + '.anvio_genes.json')} -- \\
        anvi-gen-contigs-database -L 0 -T ${task.cpus} --project-name ${q.call(p)} -f ${q.call(p + '.contigs.fasta')} -o ${q.call(p + '.contigs.db')}
    python3 anvio_checked.py --source anvio_source --record ${q.call(p + '.anvio_export_genes.json')} -- \\
        anvi-export-gene-calls --gene-caller prodigal -c ${q.call(p + '.contigs.db')} -o ${q.call(p + '.gene_calls.tsv')}
    python3 anvio_checked.py --source anvio_source --record ${q.call(p + '.anvio_cogs.json')} -- \\
        anvi-run-ncbi-cogs -T ${task.cpus} --cog-version COG14 --cog-data-dir cog_database -c ${q.call(p + '.contigs.db')}
    python3 anvio_checked.py --source anvio_source --record ${q.call(p + '.anvio_pfams.json')} -- \\
        anvi-run-pfams -T ${task.cpus} --pfam-data-dir pfam_database -c ${q.call(p + '.contigs.db')}
    python3 anvio_checked.py --source anvio_source --record ${q.call(p + '.anvio_export_functions.json')} -- \\
        anvi-export-functions --annotation-sources COG14_FUNCTION,Pfam -c ${q.call(p + '.contigs.db')} -o ${q.call(p + '.cogs_pfams.tsv')}
    python3 plasx_inputs.py check-anvio --sample ${q.call(p)} --fasta ${q.call(p + '.contigs.fasta')} --mapping ${q.call(p + '.id_map.tsv')} \\
        --genes ${q.call(p + '.gene_calls.tsv')} --annotations ${q.call(p + '.cogs_pfams.tsv')} --database ${q.call(p + '.contigs.db')} --record ${q.call(p + '.anvio_identity.json')}
    """
}

process PLASX {
    tag { meta.id }
    label 'process_medium'
    cache 'deep'
    conda "${moduleDir}/../../envs/plasx-linux-64.lock"
    publishDir "${params.outdir}/04_plasmid_detection/plasx", mode: params.publish_dir_mode

    input:
    tuple val(meta), path(assembly), path(mapping), path(gene_calls), path(annotations)
    tuple path(plasx_source, stageAs: 'plasx_source'), val(plasx_source_identity)
    tuple path(profiles, stageAs: 'plasx_profiles'), val(profile_identity)
    path plasx_model, stageAs: 'plasx_coefficients.tsv'
    // Explicit regular files: helper changes participate in deep caching.
    tuple path(autoplasm_helper_0, stageAs: 'plasx_inputs.py'), path(autoplasm_helper_1, stageAs: 'plasx_checked.py')

    output:
    tuple val(meta), path("${meta.id}.plasx.tsv"), emit: predictions
    tuple val(meta), path("${meta.id}.de_novo.tsv"), emit: de_novo
    tuple val(meta), path("${meta.id}.plasx_state.tsv"), emit: state
    tuple val(meta), path("${meta.id}.plasx_*.json"), emit: runtime
    tuple val("${task.process}"), val(meta), path("${meta.id}.PLASX.task_command.sh"),
          val('python3 plasx_checked.py -h'), eval('python3 plasx_checked.py -h'),
          eval("sha256sum '${meta.id}.PLASX.task_command.sh'"), emit: task_provenance

    script:
    def q = { value -> "'" + value.toString().replace("'", "'\"'\"'") + "'" }
    def p = meta.id.toString()
    def splits = params.plasx_splits == null ? 32 : params.plasx_splits
    if (!(splits.toString() ==~ /[0-9]+/)) error '--plasx_splits must be a nonnegative integer'
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.PLASX.task_command.sh'
    export PYTHONDONTWRITEBYTECODE=1
    export PYTHONPATH="\$PWD/plasx_source"
    python3 plasx_inputs.py resources --profiles plasx_profiles --model plasx_coefficients.tsv --record ${q.call(p + '.plasx_resources.json')}
    python3 plasx_checked.py --record ${q.call(p + '.plasx_search.json')} -- search_de_novo_families \\
        -g ${q.call(gene_calls)} -db plasx_profiles -o ${q.call(p + '.de_novo.tsv')} --threads ${task.cpus} --splits ${splits} --tmp plasx_tmp --overwrite
    python3 plasx_checked.py --record ${q.call(p + '.plasx_predict.json')} -- predict \\
        -a ${q.call(annotations)} ${q.call(p + '.de_novo.tsv')} -g ${q.call(gene_calls)} -m plasx_coefficients.tsv -o native_scores.tsv --overwrite
    python3 plasx_inputs.py finalize --sample ${q.call(p)} --fasta ${q.call(assembly)} --mapping ${q.call(mapping)} --genes ${q.call(gene_calls)} \\
        --annotations ${q.call(annotations)} --de-novo ${q.call(p + '.de_novo.tsv')} --scores native_scores.tsv \\
        --output ${q.call(p + '.plasx.tsv')} --state ${q.call(p + '.plasx_state.tsv')} --record ${q.call(p + '.plasx_identity.json')}
    """
}
