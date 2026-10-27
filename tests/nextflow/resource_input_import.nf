nextflow.enable.dsl=2
include { resourceInput } from '../../lib/resource_inputs'
workflow {
    def resource = resourceInput(params.resource)
    assert resource[1].schema_version == 2
    assert resource[1].file_count > 0
    assert resourceInput(null)[0] == []
    assert resourceInput([])[1].resource_state == 'absent'
    println 'RESOURCE_IMPORT=' + groovy.json.JsonOutput.toJson(resource[1])
}
