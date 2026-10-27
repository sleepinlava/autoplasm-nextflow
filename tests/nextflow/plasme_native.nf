nextflow.enable.dsl=2
include { PLASME } from '../../modules/detection/plasme'

workflow {
    def ResourceIdentity = new GroovyClassLoader().parseClass(new File("${moduleDir}/../../lib/ResourceIdentity.groovy"))
    def resource = { location ->
        def directory = file(location, checkIfExists:true)
        tuple(directory, ResourceIdentity.capture(directory))
    }
    PLASME(Channel.of(tuple([id:params.sample_id],file(params.assembly,checkIfExists:true))),
           Channel.value(resource.call(params.database)),
           Channel.value(resource.call(params.source_dir)), Channel.value(tuple(file("${moduleDir}/../../bin/normalize_plasme_outputs.py", checkIfExists: true), file("${moduleDir}/../../bin/plasme_runtime.py", checkIfExists: true))))
}
