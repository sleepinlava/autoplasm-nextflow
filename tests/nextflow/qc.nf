/*
 * QC regression harness adapted to the nf-core module swap (branch
 * refactor/nf-core-modules). The retired in-house modules/qc/{fastqc,multiqc}
 * are replaced by the vendored nf-core modules:
 *   - FASTQC now emits separate `zip` / `html` channels (the old combined
 *     `results` emit is gone), and its task.ext.prefix closure needs
 *     meta.stage ('raw'/'clean') from conf/nfcore_qc_assembly.config.
 *   - MULTIQC takes the 6-element tuple (meta, files, config, logo,
 *     replace_names, sample_names); SHORT_READ_MULTIQC_INPUTS.out.files is a
 *     plain collected file list, so the harness wraps it exactly like
 *     subworkflows/illumina.nf does.
 */
nextflow.enable.dsl = 2

include { FASTQC } from '../../modules/nf-core/fastqc/main'
include { FASTQC as FASTQC_CLEAN } from '../../modules/nf-core/fastqc/main'
include { MULTIQC } from '../../modules/nf-core/multiqc/main'
include { SHORT_READ_MULTIQC_INPUTS } from '../../subworkflows/short_read_multiqc_inputs'

workflow {
    ch_fastqc_raw = Channel.empty()
    ch_fastqc_clean = Channel.empty()
    ch_fastp_json = Channel.empty()
    if (params.run_fastqc) {
        def root = file(params.fixture_dir)
        def rawEntries = []
        def cleanEntries = []
        ['S1', 'S2'].each { id ->
            rawEntries << tuple([id: id], 'raw',
                file("${root}/${id}/raw/R1.fastq.gz", checkIfExists: true),
                file("${root}/${id}/raw/R2.fastq.gz", checkIfExists: true))
            cleanEntries << tuple([id: id], 'clean',
                file("${root}/${id}/clean/R1.fastq.gz", checkIfExists: true),
                file("${root}/${id}/clean/R2.fastq.gz", checkIfExists: true))
        }
        if (params.extra_alias_tests) {
            rawEntries << tuple([id: 'A__B.v1'], 'raw',
                file("${root}/same-basename/mate1/reads.fq.gz", checkIfExists: true),
                file("${root}/same-basename/mate2/reads.fq.gz", checkIfExists: true))
            cleanEntries << tuple([id: 'U1'], 'clean',
                file("${root}/uncompressed/mate1/reads.fastq", checkIfExists: true),
                file("${root}/uncompressed/mate2/reads.fq", checkIfExists: true))
        }
        // nf-core fastqc input: tuple(meta, [reads]); meta.stage feeds the
        // <id>.<stage> alias prefix configured in conf/nfcore_qc_assembly.config
        FASTQC(Channel.fromList(rawEntries.collect { meta, stage, r1, r2 ->
            tuple(meta + [stage: stage], [r1, r2]) }))
        FASTQC_CLEAN(Channel.fromList(cleanEntries.collect { meta, stage, r1, r2 ->
            tuple(meta + [stage: stage], [r1, r2]) }))
        ch_fastqc_raw = FASTQC.out.zip
        ch_fastqc_clean = FASTQC_CLEAN.out.zip
    }
    if (params.include_fastp_json) {
        ch_fastp_json = Channel.of(tuple([id: 'S1'], file(params.fastp_json, checkIfExists: true)))
    }
    if (params.run_multiqc) {
        SHORT_READ_MULTIQC_INPUTS(ch_fastp_json, ch_fastqc_raw, ch_fastqc_clean, params.run_fastqc)
        // Same 6-element tuple construction as subworkflows/illumina.nf; the
        // meta.id becomes the report label via MULTIQC's ext.prefix closure.
        MULTIQC(SHORT_READ_MULTIQC_INPUTS.out.files.map { files ->
            tuple([id: 'multiqc_test'], files, [], [], [], [])
        })
    }
    if (params.run_fastqc) {
        FASTQC.out.zip.view { meta, zips -> "FASTQC\t${meta.id}\t${zips}" }
        FASTQC_CLEAN.out.zip.view { meta, zips -> "FASTQC_CLEAN\t${meta.id}\t${zips}" }
        FASTQC.out.html.view { meta, htmls -> "FASTQC_HTML\t${meta.id}\t${htmls}" }
        FASTQC_CLEAN.out.html.view { meta, htmls -> "FASTQC_CLEAN_HTML\t${meta.id}\t${htmls}" }
    }
}
