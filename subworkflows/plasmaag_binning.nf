include { selectedTools } from '../lib/tool_selection'
include { reportEvidence } from '../lib/report_events'
include { PLASMAAG } from '../modules/binning/plasmaag'

workflow PLASMAAG_BINNING {
    take:
    ch_assembly
    ch_reads
    ch_spades_bundle

    main:
    ch_bins = Channel.empty()
    ch_events = Channel.empty()
    if (selectedTools(params.plasmid_binning_tools).contains('plasmaag')) {
        if (params.platform != 'illumina' || !['metaspades', 'megahit'].contains(params.short_read_assembler)) {
            error('PlasMAAG requires illumina with metaspades or megahit complete assemblies and paired reads')
        }
        ch_rows = ch_assembly.map { meta, fasta -> tuple(meta.id.toString(), meta, fasta) }
            .join(ch_reads.map { meta, r1, r2 -> tuple(meta.id.toString(), meta, r1, r2) }, failOnDuplicate: true, failOnMismatch: true)
            .map { id, meta, fasta, readMeta, r1, r2 ->
                if (meta != readMeta) error("PlasMAAG read/assembly metadata differ for ${id}")
                tuple(id, meta, fasta, r1, r2)
            }
        if (params.short_read_assembler == 'metaspades') {
            ch_rows = ch_rows.join(ch_spades_bundle.map { meta, bundle -> tuple(meta.id.toString(), meta, bundle) },
                failOnDuplicate: true, failOnMismatch: true)
                .map { id, meta, fasta, r1, r2, bundleMeta, bundle ->
                    if (meta != bundleMeta) error("PlasMAAG SPAdes bundle metadata differ for ${id}")
                    [meta: meta, reads: [r1, r2], assembly: bundle]
                }
        } else {
            ch_rows = ch_rows.map { id, meta, fasta, r1, r2 -> [meta: meta, reads: [r1, r2], assembly: fasta] }
        }
        ch_cohort = ch_rows.toList().map { values ->
            if (!values) error('PlasMAAG cohort is empty')
            def rows = values.sort { a, b -> a.meta.id.toString() <=> b.meta.id.toString() }
            def ids = rows.collect { it.meta.id.toString() }
            if (ids.toSet().size() != ids.size()) error('PlasMAAG cohort has duplicate sample IDs')
            def digest = java.security.MessageDigest.getInstance('SHA-256')
                .digest(groovy.json.JsonOutput.toJson(ids).getBytes('UTF-8')).encodeHex().toString()
            tuple([id: "plasmaag_cohort_${digest}"], rows.collect { it.meta }, rows.collectMany { it.reads }, rows.collect { it.assembly })
        }
        PLASMAAG(ch_cohort,
            Channel.value(tuple(file(params.plasmaag_source, checkIfExists: true), files("${params.plasmaag_source}/**", type: 'file', hidden: true))),
            Channel.value(tuple(file(params.genomad_db, checkIfExists: true), files("${params.genomad_db}/**", type: 'file', hidden: true))),
            params.short_read_assembler,
            [genomad_splits: params.plasmaag_genomad_splits ?: 0, vamb_arguments: params.plasmaag_vamb_arguments ?: '', conda_prefix: params.plasmaag_conda_prefix ?: ''],
            Channel.value(tuple(file("${moduleDir}/../bin/plasmaag_inputs.py", checkIfExists: true), file("${moduleDir}/../bin/plasmaag_checked.py", checkIfExists: true))))
        ch_bins = PLASMAAG.out.bins.flatMap { cohort, directory ->
            def manifest = new groovy.json.JsonSlurper().parseText(directory.resolve('samples.json').text)
            manifest.samples.collect { sample -> tuple(new LinkedHashMap(sample.meta), directory.resolve(sample.relative_directory), sample.state) }
        }
        ch_events = reportEvidence([channels: PLASMAAG.out], '05_plasmid_binning', 'PLASMAAG')
    }

    emit:
    bins = ch_bins
    report_events = ch_events
}
