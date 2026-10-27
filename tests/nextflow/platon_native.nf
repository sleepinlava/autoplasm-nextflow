nextflow.enable.dsl=2
include { PLATON } from '../../modules/detection/platon'
workflow {
    def ResourceIdentity = new GroovyClassLoader().parseClass(new File("${moduleDir}/../../lib/ResourceIdentity.groovy"))
    def resource = { location ->
        def directory = file(location, checkIfExists: true)
        tuple(directory, ResourceIdentity.capture(directory))
    }
    candidates=Channel.fromList(params.records).map { row -> tuple([id:row.id,group:'preserved'],file(row.fasta,checkIfExists:true)) }
    PLATON(candidates,Channel.value(resource.call(params.database)), Channel.value(file("${moduleDir}/../../bin/platon_checked.py", checkIfExists: true)))
    PLATON.out.predictions.view { meta, value -> 'PLATON_PRODUCT='+meta.id+':'+value }
}
