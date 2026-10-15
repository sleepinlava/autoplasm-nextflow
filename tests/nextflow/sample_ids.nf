nextflow.enable.dsl = 2

include { SAMPLE_ID_VALIDATION } from '../../subworkflows/sample_id_validation'

workflow {
    def ids = (params.ids != null ? params.ids.toString() : 'A__B.v1').split(',', -1).collect { [it] }
    def rows = []
    ids.eachWithIndex { row, index -> rows << tuple(index + 2, row) }
    SAMPLE_ID_VALIDATION(Channel.fromList(rows), ['sample_id'])
    SAMPLE_ID_VALIDATION.out.rows.view { row -> "VALID\t${row[0]}" }
}
