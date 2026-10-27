/* Fixed PlasMAAG runs once on complete assemblies/paired reads for the cohort. */
process PLASMAAG {
    tag { meta.id }
    label 'process_high'
    cache 'deep'
    conda "${moduleDir}/../../envs/plasmaag.yml"
    publishDir "${params.outdir}/05_plasmid_binning/plasmaag", mode: params.publish_dir_mode

    input:
    tuple val(meta), val(samples), path(reads, stageAs: 'cohort_reads/read??/*'), path(assemblies, stageAs: 'cohort_assemblies/assembly??')
    tuple path(program, stageAs: 'plasmaag_program'), val(program_identity)
    tuple path(database, stageAs: 'genomad_database'), val(database_identity)
    val assembler
    val runtime_options
    tuple path(input_helper, stageAs: 'plasmaag_inputs.py'), path(runtime_helper, stageAs: 'plasmaag_checked.py')

    output:
    tuple val(meta), path("${meta.id}.plasmaag", type: 'dir'), emit: bins
    tuple val(meta), path("${meta.id}.plasmaag_runtime.json"), emit: runtime

    script:
    if (task.cpus < 8) error('Fixed PlasMAAG Node2Vec uses 8 workers; allocate at least 8 CPUs')
    def q = { value -> "'" + value.toString().replace("'", "'\"'\"'") + "'" }
    def pairs = reads in List ? reads : [reads]
    def genomes = assemblies in List ? assemblies : [assemblies]
    if (pairs.size() != samples.size() * 2 || genomes.size() != samples.size()) error('PlasMAAG cohort input cardinality differs')
    def records = samples.withIndex().collect { sample, index ->
        [meta: sample, reads: [pairs[2 * index].toString(), pairs[2 * index + 1].toString()], assembly: genomes[index].toString()]
    }
    def spec = groovy.json.JsonOutput.toJson([assembler: assembler, records: records])
    def mode = assembler == 'metaspades' ? '--reads_and_assembly_dir' : '--reads_and_contigs'
    def splits = runtime_options.genomad_splits ? "--genomad-splits ${runtime_options.genomad_splits}" : ''
    def vamb = runtime_options.vamb_arguments ? "--vamb_arguments ${q.call(runtime_options.vamb_arguments)}" : ''
    def snake = runtime_options.conda_prefix ? "--snakemake_arguments ${q.call('--conda-prefix ' + runtime_options.conda_prefix)}" : ''
    """
    cat > cohort-spec.json <<'PLASMAAG_COHORT_JSON'
${spec}
PLASMAAG_COHORT_JSON
    python3 plasmaag_inputs.py prepare --spec cohort-spec.json --output cohort_inputs
    export XDG_CACHE_HOME=\$PWD/.cache
    export PYTHONDONTWRITEBYTECODE=1
    python3 plasmaag_checked.py --source plasmaag_program --runtime-record ${q.call(meta.id + '.plasmaag_runtime.json')} ${splits} -- \\
        ${mode} \$PWD/cohort_inputs/reads-and-assembly.tsv \\
        --output \$PWD/.plasmaag_native --threads ${task.cpus} --genomad_db \$PWD/genomad_database \\
        ${vamb} ${snake}
    python3 plasmaag_inputs.py validate --sample-map cohort_inputs/sample-map.json \\
        --results .plasmaag_native/results --output ${q.call(meta.id + '.plasmaag')}
    """
}
