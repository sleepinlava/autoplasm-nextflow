#!/usr/bin/env nextflow
/*
 * AutoPlasm — Metagenomic Plasmid Analysis (standalone Nextflow DSL2
 * pipeline; the short-read protocol audit is docs/protocol-requirements-audit-20261030.md in
 * this repository).
 *
 * Usage: nextflow run . --samplesheet samples.tsv --platform illumina -profile conda
 */
nextflow.enable.dsl = 2

include { selectedTools } from './lib/tool_selection'
include { magSelectionError } from './lib/mag_selection'

include { ILLUMINA } from './subworkflows/illumina'
include { ONT } from './subworkflows/ont'
include { PACBIO_HIFI } from './subworkflows/pacbio_hifi'
include { HYBRID } from './subworkflows/hybrid'
include { ASSEMBLY } from './subworkflows/assembly'
include { CROSS_SAMPLE } from './subworkflows/cross_sample'
include { SAMPLE_ID_VALIDATION } from './subworkflows/sample_id_validation'

// Resolve outdir to an absolute path for published outputs and report inputs.
params.outdir = new File(params.outdir).getAbsolutePath()

def paramError(msg) {
    System.err.println("ERROR: ${msg}")
    System.exit(1)
}

// Return a Path for a non-empty string, else null
def optFile(s) {
    return (s != null && s.toString().trim()) ? file(s.toString().trim()) : null
}

// Names are validated independently of platform/DB eligibility. Keep declared
// capabilities and supported aliases here, including explicitly rejected CRISPR.
def toolChoices() {
    return [
        polishing_tools: ['medaka'],
        plasmid_detection_tools: ['genomad','plasme','plasx','platon'],
        plasmid_binning_tools: ['plasmaag','gplas2','mob_recon','mob_suite','recycler'],
        typing_tools: ['plasmidfinder','mob_typer'],
        typing_optional_tools: ['copla','conjscan','macsyfinder'],
        host_prediction_tools: ['metaphlan','kraken2','plasmidhostfinder'],
        mag_tools: ['plasmaag','metabat2','concoct','semibin','das_tool','checkm2','gtdbtk'],
        host_linking_methods: ['co_abundance','sequence','long_read'],
        host_linking_optional_methods: ['crispr','hotspot'],
        annotation_tools: ['bakta','amrfinderplus','abricate','isescan','integronfinder','prodigal'],
        annotation_optional_tools: ['prodigal','abricate','rgi','eggnog_mapper','mob_suite'],
        comparative_tools: ['mmseqs2'],
        comparative_optional_tools: ['blast','mummer','clinker']
    ]
}

def normalizeToolSelections() {
    toolChoices().each { key, allowed ->
        def raw = params[key]
        def values
        if (raw == null) {
            values = []
        } else if (raw instanceof List) {
            values = raw
        } else if (raw instanceof CharSequence) {
            values = raw.toString().trim() ? raw.toString().split(',', -1) as List : []
        } else {
            paramError("--${key} must be a list of tool names or a comma-separated string")
        }
        values.eachWithIndex { value, index ->
            if (!(value instanceof CharSequence)) {
                paramError("--${key} has an invalid tool name at entry ${index + 1}: ${value} (expected a string)")
            }
            def name = value.toString().trim()
            if (name == 'scapp' && (key in ['plasmid_detection_tools','plasmid_binning_tools']))
                paramError("SCAPP nodes have been removed; remove 'scapp' from --${key}")
            if (!name) paramError("--${key} has an empty tool name at entry ${index + 1}")
            if (!allowed.contains(name)) {
                paramError("--${key} has unknown tool '${name}' (choose from ${allowed})")
            }
        }
        // Consumers normalize their own copied params; do not mutate ParamsMap.
    }
}

def col(header, name) {
    return header.indexOf(name)
}

def metaOf(header, row) {
    def meta = [id: row[col(header, 'sample_id')]]
    def groupIdx = col(header, 'group')
    meta.group = groupIdx >= 0 ? (row[groupIdx] ?: '') : ''
    def hrIdx = col(header, 'host_reference')
    def hr = (hrIdx >= 0 && row[hrIdx]) ? row[hrIdx].trim() : null
    meta.host_reference = hr ?: params.host_reference
    return meta
}

def cell(header, row, name) {
    return col(header, name) >= 0 ? optFile(row[col(header, name)]) : null
}

def validateParams() {
    if (params.short_read_protocol && (params.platform != 'illumina' ||
        params.short_read_assembler != 'metaspades' ||
        !selectedTools(params.plasmid_binning_tools).contains('plasmaag'))) {
        paramError('short_read_protocol requires illumina, metaspades and PlasMAAG')
    }
    if (selectedTools(params.mag_tools).contains('plasmaag') && !params.short_read_protocol) {
        paramError('MAG source plasmaag requires --short_read_protocol')
    }
    def magError = magSelectionError(params.mag_tools)
    if (magError) paramError(magError)
    if (params.host_plasmid_linking && selectedTools(params.host_linking_optional_methods).contains('crispr')) {
        paramError("CRISPR host-plasmid linking is not implemented; remove 'crispr' from --host_linking_optional_methods")
    }
    if (params.host_plasmid_linking && selectedTools(params.host_linking_optional_methods).contains('hotspot')) {
        ['hotspot_home', 'hotspot_db', 'hotspot_models'].each { p ->
            if (!params[p]) {
                paramError("host_linking_optional_methods 'hotspot' requires --${p} (cloned HOTSPOT repo + database/models folders)")
            }
        }
    }
    def platforms = ['illumina', 'ont', 'pacbio_hifi', 'hybrid', 'assembly']
    if (!platforms.contains(params.platform)) {
        paramError("--platform must be one of ${platforms}")
    }
    if (!params.samplesheet) {
        paramError("--samplesheet is required")
    }
    if (!new File(params.samplesheet).exists()) {
        paramError("samplesheet not found: ${params.samplesheet}")
    }
    // geNomad is mandatory on every platform
    if (!params.genomad_db) {
        paramError("geNomad is mandatory: set --genomad_db")
    }
    // Every enabled tool that needs a database must have it configured
    def required = []
    if (params.short_read_protocol && params.protocol_host_models) {
        required << ['mostplas_source',params.mostplas_source]
        required << ['plsdb_fasta',params.plsdb_fasta]
        required << ['plsdb_hosts',params.plsdb_hosts]
    }
    if (selectedTools(params.plasmid_detection_tools).contains('plasme')) {
        required << ['plasme_db', params.plasme_db]
        required << ['plasme_dir', params.plasme_dir]
    }
    if (selectedTools(params.plasmid_detection_tools).contains('platon')) required << ['platon_db', params.platon_db]
    if (selectedTools(params.plasmid_binning_tools).contains('gplas2')) required << ['gplas_source', params.gplas_source]
    if (selectedTools(params.plasmid_binning_tools).contains('plasmaag')) required << ['plasmaag_source', params.plasmaag_source]
    if (selectedTools(params.plasmid_detection_tools).contains('plasx')) {
        if (params.plasx_annotations) paramError('--plasx_annotations is retired: PlasX now generates complete annotations for each sample')
        required << ['plasx_anvio_source', params.plasx_anvio_source]
        required << ['plasx_source', params.plasx_source]
        required << ['plasx_cog_db', params.plasx_cog_db]
        required << ['plasx_pfam_db', params.plasx_pfam_db]
        required << ['plasx_profiles', params.plasx_profiles]
        required << ['plasx_model', params.plasx_model]
        if (!(params.plasx_splits.toString() ==~ /[0-9]+/)) paramError('--plasx_splits must be a nonnegative integer')
    }
    // nf-core plasmidfinder / mobsuite-recon use their packaged databases
    if (selectedTools(params.typing_tools).contains('mob_typer')) required << ['mob_suite_db', params.mob_suite_db]
    if (selectedTools(params.typing_optional_tools).contains('copla')) {
        required << ['copla_refgraph', params.copla_refgraph]
        required << ['copla_reflist', params.copla_reflist]
        required << ['copla_dir', params.copla_dir]
        required << ['copla_macsyfinder_dir', params.copla_macsyfinder_dir]
    }
    if (selectedTools(params.annotation_tools).contains('bakta')) required << ['bakta_db', params.bakta_db]
    if (selectedTools(params.annotation_tools).contains('amrfinderplus')) required << ['amrfinderplus_db', params.amrfinderplus_db]
    if (selectedTools(params.annotation_optional_tools).contains('rgi')) required << ['card_db', params.card_db]
    if (selectedTools(params.annotation_optional_tools).contains('eggnog_mapper')) required << ['eggnog_db', params.eggnog_db]
    if (selectedTools(params.host_prediction_tools).contains('metaphlan') && params.platform != 'assembly') {
        required << ['metaphlan_db', params.metaphlan_db]
    }
    if (selectedTools(params.host_prediction_tools).contains('kraken2')) required << ['kraken2_db', params.kraken2_db]
    if (selectedTools(params.host_prediction_tools).contains('plasmidhostfinder') && params.platform == 'assembly') {
        required << ['plasmidhostfinder_db', params.plasmidhostfinder_db]
    }
    if (selectedTools(params.mag_tools).contains('gtdbtk')) required << ['gtdbtk_db', params.gtdbtk_db]
    if (selectedTools(params.mag_tools).contains('checkm2')) required << ['checkm2_db', params.checkm2_db]
    if (selectedTools(params.comparative_optional_tools).contains('blast')) required << ['blast_db', params.blast_db]
    if (selectedTools(params.comparative_optional_tools).contains('mummer')) required << ['reference_plasmids', params.reference_plasmids]
    if (selectedTools(params.comparative_optional_tools).contains('clinker') && !selectedTools(params.annotation_tools).contains('bakta')) {
        paramError("comparative_optional_tools 'clinker' requires annotation_tools 'bakta'")
    }
    required.each { entry ->
        if (!entry[1]) {
            paramError("an enabled tool requires --${entry[0]}")
        }
    }
    if (selectedTools(params.plasmid_detection_tools).contains('plasx')) {
        ['plasx_anvio_source', 'plasx_source', 'plasx_cog_db', 'plasx_pfam_db', 'plasx_profiles'].each { name ->
            if (!new File(params[name].toString()).isDirectory()) paramError("--${name} must be a directory")
        }
        if (!new File(params.plasx_model.toString()).isFile()) paramError('--plasx_model must be a coefficient table file')
        ['anvio/__init__.py', 'bin/anvi-gen-contigs-database', 'bin/anvi-export-gene-calls',
         'bin/anvi-run-ncbi-cogs', 'bin/anvi-run-pfams', 'bin/anvi-export-functions'].each { name ->
            if (!new File(params.plasx_anvio_source.toString(), name).isFile()) paramError("--plasx_anvio_source missing source file ${name}")
        }
        ['plasx/model.py', 'plasx/mmseqs.py', 'plasx/plasx_script.py'].each { name ->
            if (!new File(params.plasx_source.toString(), name).isFile()) paramError("--plasx_source missing source file ${name}")
        }
    }
    if (selectedTools(params.plasmid_detection_tools).contains('plasme')) {
        def source = new File(params.plasme_dir.toString())
        if (!source.isDirectory()) paramError('--plasme_dir must be a source directory')
        ['PLASMe.py', 'bio_script.py', 'trans_data.py', 'trans_model.py'].each { name ->
            if (!new File(source, name).isFile()) paramError("--plasme_dir missing source file ${name}")
        }
    }
    if (selectedTools(params.plasmid_binning_tools).contains('plasmaag')) {
        ['PlasMAAG/__main__.py', 'snakefile.smk', 'snakefile_megahit.smk', 'config/config.yaml'].each { name ->
            if (!new File(params.plasmaag_source.toString(), name).isFile()) paramError("--plasmaag_source missing fixed source file ${name}")
        }
        if (!(params.plasmaag_genomad_splits.toString() ==~ /[0-9]+/)) paramError('--plasmaag_genomad_splits must be a nonnegative integer')
        if (params.plasmaag_conda_prefix && params.plasmaag_conda_prefix.toString().find(/\s/)) paramError('--plasmaag_conda_prefix must not contain whitespace')
    }
    if (selectedTools(params.plasmid_binning_tools).contains('gplas2')) {
        ['gplas/gplas.py', 'gplas/version.py', 'gplas/snakefiles/otherclassifiers.smk'].each { name ->
            if (!new File(params.gplas_source.toString(), name).isFile()) paramError("--gplas_source missing fixed source file ${name}")
        }
    }
    if (selectedTools(params.typing_optional_tools).contains('copla')) {
        def installation = new File(params.copla_dir.toString())
        if (!installation.isDirectory()) paramError('--copla_dir must be a prepared installation directory')
        ['bin/copla.py', 'bin/ani.rb'].each { name ->
            if (!new File(installation, name).isFile()) paramError("--copla_dir missing source file ${name}")
        }
        ['MOBscan_171004', 'MacSyFinder_190530/Conjugation', 'PlasmidFinder_190731', 'CARD_201015'].each { name ->
            if (!new File(installation, 'databases/' + name).isDirectory()) paramError("--copla_dir missing database directory ${name}")
        }
        if (!new File(params.copla_macsyfinder_dir.toString(), 'bin/macsyfinder').isFile()) {
            paramError('--copla_macsyfinder_dir missing bin/macsyfinder')
        }
    }
    if (!['megahit', 'metaspades'].contains(params.short_read_assembler)) {
        paramError("short_read_assembler must be megahit or metaspades")
    }
    if (!['opera_ms', 'hybridspades'].contains(params.hybrid_assembler)) {
        paramError("hybrid_assembler must be opera_ms or hybridspades")
    }
    if (selectedTools(params.plasmid_binning_tools).contains('plasmaag') && params.platform != 'illumina') {
        paramError('PlasMAAG requires illumina with metaspades or megahit complete assemblies and paired reads')
    }
    if (selectedTools(params.plasmid_binning_tools).contains('recycler') &&
        !((params.platform == 'illumina' && params.short_read_assembler == 'metaspades') ||
          (params.platform == 'hybrid' && params.hybrid_assembler == 'hybridspades'))) {
        paramError("Recycler requires illumina with --short_read_assembler metaspades or hybrid with --hybrid_assembler hybridspades (same-run SPAdes FASTG/k provenance and original short-read pairs)")
    }
    if (selectedTools(params.plasmid_binning_tools).contains('gplas2') &&
        !((params.platform == 'illumina' && params.short_read_assembler == 'metaspades') ||
          (params.platform == 'hybrid' && params.hybrid_assembler == 'hybridspades'))) {
        paramError("gplas2 requires illumina/metaspades or hybrid/hybridspades with same-run SPAdes GFA; graph nodes are classified independently")
    }
}

workflow {
    def run_sample_ids = []
    if (params.short_read_protocol) {
        def info_directory = new File(params.outdir.toString(),'pipeline_info')
        def run_metadata = workflow
        workflow.onComplete {
            info_directory.mkdirs()
            def state = [success:run_metadata.success,exit_status:run_metadata.exitStatus,run_name:run_metadata.runName,
                command_line:run_metadata.commandLine,session_id:run_metadata.sessionId.toString(),
                revision:run_metadata.revision,error_message:run_metadata.errorMessage,duration:run_metadata.duration.toString()]
            new File(info_directory,'run_state.json').text = groovy.json.JsonOutput.prettyPrint(groovy.json.JsonOutput.toJson(state)) + '\n'
            def trace_file = new File(info_directory,'trace.tsv')
            def failures = []
            if (trace_file.exists()) {
                def lines = trace_file.readLines()
                def columns = lines[0].split('\t') as List
                lines.drop(1).each { line ->
                    def values = line.split('\t',-1)
                    def record = columns.withIndex().collectEntries { name,i -> [(name):values[i]] }
                    if (record.status in ['FAILED','ABORTED']) {
                        def tag = record.name =~ / \(([^()]*)\)$/
                        def sample = tag.find() && run_sample_ids.contains(tag.group(1)) ? tag.group(1) : ''
                        failures << [sample,sample ? 'sample' : 'cohort_or_unresolved',record.name,record.hash,record.status,record.exit].join('\t')
                    }
                }
            }
            if (!failures && !run_metadata.success)
                failures << ['', 'workflow', 'workflow', '', 'FAILED', run_metadata.exitStatus == null ? 'not_available' : run_metadata.exitStatus].join('\t')
            new File(info_directory,'failed_samples.tsv').text = 'sample_id\tfailure_scope\ttask_name\ttask_hash\tstatus\texit_status\n' +
                (failures ? failures.join('\n')+'\n' : '')
        }
    }
    normalizeToolSelections()

    validateParams()

    // ---------------- samplesheet ----------------
    def sheet = new File(params.samplesheet).readLines()
    def header = sheet[0].split('\t') as List
    def rowsWithLines = []
    sheet.drop(1).eachWithIndex { line, index ->
        if (line.trim()) rowsWithLines << tuple(index + 2, line.split('\t', -1) as List)
    }
    def rows = rowsWithLines.collect { entry -> entry[1] }
    if (col(header, 'sample_id') < 0) paramError("samplesheet needs a sample_id column")
    if (rows.isEmpty()) paramError("samplesheet has no data rows")
    run_sample_ids = rows.collect { it[col(header,'sample_id')] }.toSet()
    SAMPLE_ID_VALIDATION(Channel.fromList(rowsWithLines), header)
    def groupIdx = col(header, 'group')
    def n_samples = rows.size()
    def n_groups = groupIdx >= 0 ? rows.collect { it[groupIdx] }.unique().size() : 1

    ch_rows = SAMPLE_ID_VALIDATION.out.rows

    ch_done = Channel.empty()
    ch_plasmids = Channel.empty()
    ch_contig_tables = Channel.empty()
    ch_plasmid_tables = Channel.empty()
    ch_quantification_states = Channel.empty()

    if (params.platform == 'illumina') {
        ch_samples = ch_rows.map { row ->
            def meta = metaOf(header, row)
            def r1 = cell(header, row, 'read1'); def r2 = cell(header, row, 'read2')
            if (r1 == null || r2 == null) paramError("sample ${meta.id}: illumina requires read1/read2")
            tuple(meta, r1, r2)
        }
        ILLUMINA(ch_samples)
        ch_plasmids = ILLUMINA.out.plasmids
        ch_contig_tables = ILLUMINA.out.contig_tables
        ch_plasmid_tables = ILLUMINA.out.plasmid_tables
        ch_quantification_states = ILLUMINA.out.quantification_states
        ch_done = ILLUMINA.out.done
    } else if (params.platform == 'ont') {
        ch_samples = ch_rows.map { row ->
            def meta = metaOf(header, row)
            def pod5 = cell(header, row, 'pod5'); def bam = cell(header, row, 'bam'); def lr = cell(header, row, 'long_reads')
            if (pod5 == null && bam == null && lr == null) paramError("sample ${meta.id}: ont requires pod5, bam or long_reads")
            tuple(meta, pod5, bam, lr)
        }
        ONT(ch_samples)
        ch_plasmids = ONT.out.plasmids
        ch_contig_tables = ONT.out.contig_tables
        ch_plasmid_tables = ONT.out.plasmid_tables
        ch_quantification_states = ONT.out.quantification_states
        ch_done = ONT.out.done
    } else if (params.platform == 'pacbio_hifi') {
        ch_samples = ch_rows.map { row ->
            def meta = metaOf(header, row)
            def bam = cell(header, row, 'bam'); def lr = cell(header, row, 'long_reads')
            if (bam == null && lr == null) paramError("sample ${meta.id}: pacbio_hifi requires bam or long_reads")
            tuple(meta, bam, lr)
        }
        PACBIO_HIFI(ch_samples)
        ch_plasmids = PACBIO_HIFI.out.plasmids
        ch_contig_tables = PACBIO_HIFI.out.contig_tables
        ch_plasmid_tables = PACBIO_HIFI.out.plasmid_tables
        ch_quantification_states = PACBIO_HIFI.out.quantification_states
        ch_done = PACBIO_HIFI.out.done
    } else if (params.platform == 'hybrid') {
        ch_samples = ch_rows.map { row ->
            def meta = metaOf(header, row)
            def r1 = cell(header, row, 'read1'); def r2 = cell(header, row, 'read2')
            def pod5 = cell(header, row, 'pod5'); def bam = cell(header, row, 'bam'); def lr = cell(header, row, 'long_reads')
            if (r1 == null || r2 == null) paramError("sample ${meta.id}: hybrid requires read1/read2")
            if (pod5 == null && bam == null && lr == null) paramError("sample ${meta.id}: hybrid requires pod5, bam or long_reads")
            tuple(meta, r1, r2, pod5, bam, lr)
        }
        HYBRID(ch_samples)
        ch_plasmids = HYBRID.out.plasmids
        ch_contig_tables = HYBRID.out.contig_tables
        ch_plasmid_tables = HYBRID.out.plasmid_tables
        ch_quantification_states = HYBRID.out.quantification_states
        ch_done = HYBRID.out.done
    } else if (params.platform == 'assembly') {
        ch_samples = ch_rows.map { row ->
            def meta = metaOf(header, row)
            def asm = cell(header, row, 'assembly')
            if (asm == null) paramError("sample ${meta.id}: assembly platform requires the assembly column")
            tuple(meta, asm)
        }
        ASSEMBLY(ch_samples)
        ch_plasmids = ASSEMBLY.out.plasmids
        ch_done = ASSEMBLY.out.done
    }

    CROSS_SAMPLE(
        ch_contig_tables,
        ch_plasmid_tables,
        ch_quantification_states,
        ch_plasmids,
        ch_done,
        n_samples,
        n_groups
    )
}
