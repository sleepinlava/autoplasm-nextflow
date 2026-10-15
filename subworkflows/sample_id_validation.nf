/* Validate samplesheet identifiers before the rows feed any workflow branch. */

def validateSampleRows(header, rows) {
    def sampleColumn = header.indexOf('sample_id')
    if (sampleColumn < 0) {
        throw new IllegalArgumentException('samplesheet needs a sample_id column')
    }
    def seen = [:]
    rows.each { entry ->
        def lineNumber = entry[0]
        def row = entry[1]
        def sampleId = row.size() > sampleColumn ? (row[sampleColumn] ?: '') : ''
        if (!sampleId) {
            throw new IllegalArgumentException("samplesheet line ${lineNumber}: sample_id must not be empty")
        }
        if (!(sampleId ==~ /[A-Za-z0-9][A-Za-z0-9_.-]*/)) {
            throw new IllegalArgumentException(
                "samplesheet line ${lineNumber}: invalid sample_id '${sampleId}'; " +
                'allowed pattern is [A-Za-z0-9][A-Za-z0-9_.-]*'
            )
        }
        if (seen.containsKey(sampleId)) {
            throw new IllegalArgumentException(
                "samplesheet line ${lineNumber}: duplicate sample_id '${sampleId}' " +
                "(first seen on line ${seen[sampleId]})"
            )
        }
        seen[sampleId] = lineNumber
    }
    return rows.collect { entry -> entry[1] }
}

workflow SAMPLE_ID_VALIDATION {
    take:
    ch_rows
    header

    main:
    ch_validated = ch_rows.toList()
        .map { entries -> tuple(validateSampleRows(header, entries), true) }
        .flatMap { rows, marker -> rows.collect { row -> tuple(row, marker) } }
        .map { row, marker -> row }

    emit:
    rows = ch_validated
}
