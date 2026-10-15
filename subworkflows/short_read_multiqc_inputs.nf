/* Route fastp JSON and optional raw/clean FastQC ZIPs to short-read MultiQC. */
workflow SHORT_READ_MULTIQC_INPUTS {
    take:
    ch_fastp_json
    ch_fastqc_raw
    ch_fastqc_clean
    run_fastqc

    main:
    ch_qc_files = ch_fastp_json.map { meta, file -> file }
    if (run_fastqc) {
        ch_qc_files = ch_qc_files
            .mix(ch_fastqc_raw.map { meta, zips, htmls -> zips }.flatten())
            .mix(ch_fastqc_clean.map { meta, zips, htmls -> zips }.flatten())
    }

    emit:
    files = ch_qc_files.collect()
}
