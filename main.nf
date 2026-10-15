#!/usr/bin/env nextflow
/*
 * AutoPlasm — Metagenomic Plasmid Analysis (standalone Nextflow DSL2 port of
 * the ABI metagenomic_plasmid pipeline; the authoritative specification is
 * src/abi/plugins/metagenomic_plasmid/pipeline_dag.yaml in the ABI repo).
 *
 * Usage: nextflow run . --samplesheet samples.tsv --platform illumina -profile conda
 */
nextflow.enable.dsl = 2

include { ILLUMINA } from './subworkflows/illumina'
include { ONT } from './subworkflows/ont'
include { PACBIO_HIFI } from './subworkflows/pacbio_hifi'
include { HYBRID } from './subworkflows/hybrid'
include { ASSEMBLY } from './subworkflows/assembly'
include { CROSS_SAMPLE } from './subworkflows/cross_sample'

// Resolve outdir to an absolute path (the report/catalog steps glob it)
params.outdir = new File(params.outdir).getAbsolutePath()

def paramError(msg) {
    System.err.println("ERROR: ${msg}")
    System.exit(1)
}

// Return a Path for a non-empty string, else null
def optFile(s) {
    return (s != null && s.toString().trim()) ? file(s.toString().trim()) : null
}

def validateParams() {
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
    if (params.plasmid_detection_tools.contains('plasme')) required << ['plasme_db', params.plasme_db]
    if (params.plasmid_detection_tools.contains('platon')) required << ['platon_db', params.platon_db]
    if (params.plasmid_detection_tools.contains('plasx')) {
        required << ['plasx_annotations', params.plasx_annotations]
        required << ['plasx_model', params.plasx_model]
    }
    if (params.typing_tools.contains('plasmidfinder')) required << ['plasmidfinder_db', params.plasmidfinder_db]
    if (params.typing_tools.contains('mob_typer')) required << ['mob_suite_db', params.mob_suite_db]
    if (params.typing_optional_tools.contains('copla')) {
        required << ['copla_refgraph', params.copla_refgraph]
        required << ['copla_reflist', params.copla_reflist]
    }
    if (params.annotation_tools.contains('bakta')) required << ['bakta_db', params.bakta_db]
    if (params.annotation_tools.contains('amrfinderplus')) required << ['amrfinderplus_db', params.amrfinderplus_db]
    if (params.annotation_optional_tools.contains('rgi')) required << ['card_db', params.card_db]
    if (params.annotation_optional_tools.contains('eggnog_mapper')) required << ['eggnog_db', params.eggnog_db]
    if (params.annotation_optional_tools.contains('mob_suite')) required << ['mob_suite_db', params.mob_suite_db]
    if (params.plasmid_binning_tools.contains('mob_suite') || params.plasmid_binning_tools.contains('mob_recon')) {
        required << ['mob_suite_db', params.mob_suite_db]
    }
    if (params.host_prediction_tools.contains('metaphlan') && params.platform != 'assembly') {
        required << ['metaphlan_db', params.metaphlan_db]
    }
    if (params.host_prediction_tools.contains('kraken2')) required << ['kraken2_db', params.kraken2_db]
    if (params.host_prediction_tools.contains('plasmidhostfinder') && params.platform == 'assembly') {
        required << ['plasmidhostfinder_db', params.plasmidhostfinder_db]
    }
    if (params.mag_tools.contains('gtdbtk')) required << ['gtdbtk_db', params.gtdbtk_db]
    if (params.comparative_optional_tools.contains('blast')) required << ['blast_db', params.blast_db]
    if (params.comparative_optional_tools.contains('mummer')) required << ['reference_plasmids', params.reference_plasmids]
    if (params.comparative_optional_tools.contains('clinker') && !params.annotation_tools.contains('bakta')) {
        paramError("comparative_optional_tools 'clinker' requires annotation_tools 'bakta'")
    }
    for (entry in required) {
        if (!entry[1]) {
            paramError("an enabled tool requires --${entry[0]}")
        }
    }
    if (!['megahit', 'metaspades'].contains(params.short_read_assembler)) {
        paramError("short_read_assembler must be megahit or metaspades")
    }
    if (!['opera_ms', 'hybridspades'].contains(params.hybrid_assembler)) {
        paramError("hybrid_assembler must be opera_ms or hybridspades")
    }
}

workflow {
    validateParams()

    // ---------------- samplesheet ----------------
    def sheet = new File(params.samplesheet).readLines()
    def header = sheet[0].split('\t') as List
    def col = { name -> header.indexOf(name) }
    def rows = sheet.drop(1).findAll { it.trim() }.collect { it.split('\t', -1) as List }
    if (col('sample_id') < 0) paramError("samplesheet needs a sample_id column")
    if (rows.isEmpty()) paramError("samplesheet has no data rows")
    def groupIdx = col('group')
    def n_samples = rows.size()
    def n_groups = groupIdx >= 0 ? rows.collect { it[groupIdx] }.unique().size() : 1

    def metaOf = { row ->
        def meta = [id: row[col('sample_id')]]
        meta.group = groupIdx >= 0 ? (row[groupIdx] ?: '') : ''
        def hrIdx = col('host_reference')
        def hr = hrIdx >= 0 ? (row[hrIdx]?.trim()) : null
        meta.host_reference = hr ?: params.host_reference
        return meta
    }
    def cell = { row, name -> col(name) >= 0 ? optFile(row[col(name)]) : null }

    ch_rows = Channel.of(*rows)

    ch_done = Channel.empty()
    ch_plasmids = Channel.empty()
    ch_contig_tables = Channel.empty()
    ch_plasmid_tables = Channel.empty()

    if (params.platform == 'illumina') {
        ch_samples = ch_rows.map { row ->
            def meta = metaOf(row)
            def r1 = cell(row, 'read1'); def r2 = cell(row, 'read2')
            if (r1 == null || r2 == null) paramError("sample ${meta.id}: illumina requires read1/read2")
            tuple(meta, r1, r2)
        }
        ILLUMINA(ch_samples)
        ch_plasmids = ILLUMINA.out.plasmids
        ch_contig_tables = ILLUMINA.out.contig_tables
        ch_plasmid_tables = ILLUMINA.out.plasmid_tables
        ch_done = ILLUMINA.out.done
    } else if (params.platform == 'ont') {
        ch_samples = ch_rows.map { row ->
            def meta = metaOf(row)
            def pod5 = cell(row, 'pod5'); def bam = cell(row, 'bam'); def lr = cell(row, 'long_reads')
            if (pod5 == null && bam == null && lr == null) paramError("sample ${meta.id}: ont requires pod5, bam or long_reads")
            tuple(meta, pod5, bam, lr)
        }
        ONT(ch_samples)
        ch_plasmids = ONT.out.plasmids
        ch_contig_tables = ONT.out.contig_tables
        ch_plasmid_tables = ONT.out.plasmid_tables
        ch_done = ONT.out.done
    } else if (params.platform == 'pacbio_hifi') {
        ch_samples = ch_rows.map { row ->
            def meta = metaOf(row)
            def bam = cell(row, 'bam'); def lr = cell(row, 'long_reads')
            if (bam == null && lr == null) paramError("sample ${meta.id}: pacbio_hifi requires bam or long_reads")
            tuple(meta, bam, lr)
        }
        PACBIO_HIFI(ch_samples)
        ch_plasmids = PACBIO_HIFI.out.plasmids
        ch_contig_tables = PACBIO_HIFI.out.contig_tables
        ch_plasmid_tables = PACBIO_HIFI.out.plasmid_tables
        ch_done = PACBIO_HIFI.out.done
    } else if (params.platform == 'hybrid') {
        ch_samples = ch_rows.map { row ->
            def meta = metaOf(row)
            def r1 = cell(row, 'read1'); def r2 = cell(row, 'read2')
            def pod5 = cell(row, 'pod5'); def bam = cell(row, 'bam'); def lr = cell(row, 'long_reads')
            if (r1 == null || r2 == null) paramError("sample ${meta.id}: hybrid requires read1/read2")
            if (pod5 == null && bam == null && lr == null) paramError("sample ${meta.id}: hybrid requires pod5, bam or long_reads")
            tuple(meta, r1, r2, pod5, bam, lr)
        }
        HYBRID(ch_samples)
        ch_plasmids = HYBRID.out.plasmids
        ch_contig_tables = HYBRID.out.contig_tables
        ch_plasmid_tables = HYBRID.out.plasmid_tables
        ch_done = HYBRID.out.done
    } else if (params.platform == 'assembly') {
        ch_samples = ch_rows.map { row ->
            def meta = metaOf(row)
            def asm = cell(row, 'assembly')
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
        ch_plasmids,
        ch_done,
        n_samples,
        n_groups
    )
}
