nextflow.enable.dsl = 2

include { FASTQC; FASTQC as FASTQC_CLEAN } from '../../modules/qc/fastqc'
include { MULTIQC } from '../../modules/qc/multiqc'
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
        FASTQC(Channel.fromList(rawEntries))
        FASTQC_CLEAN(Channel.fromList(cleanEntries))
        ch_fastqc_raw = FASTQC.out.results
        ch_fastqc_clean = FASTQC_CLEAN.out.results
    }
    if (params.include_fastp_json) {
        ch_fastp_json = Channel.of(tuple([id: 'S1'], file(params.fastp_json, checkIfExists: true)))
    }
    if (params.run_multiqc) {
        SHORT_READ_MULTIQC_INPUTS(ch_fastp_json, ch_fastqc_raw, ch_fastqc_clean, params.run_fastqc)
        MULTIQC(SHORT_READ_MULTIQC_INPUTS.out.files, 'multiqc_test')
    }
    if (params.run_fastqc) {
        FASTQC.out.results.view { meta, zips, htmls -> "FASTQC\t${meta.id}\t${zips}\t${htmls}" }
        FASTQC_CLEAN.out.results.view { meta, zips, htmls -> "FASTQC_CLEAN\t${meta.id}\t${zips}\t${htmls}" }
    }
}
