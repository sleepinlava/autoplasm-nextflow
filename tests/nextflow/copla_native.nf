nextflow.enable.dsl=2
include { COPLA } from '../../modules/typing/copla'

workflow {
    def ResourceIdentity = new GroovyClassLoader().parseClass(new File("${moduleDir}/../../lib/ResourceIdentity.groovy"))
    def resource = { location ->
        def directory = file(location, checkIfExists:true)
        tuple(directory, ResourceIdentity.capture(directory))
    }
    COPLA(Channel.of(tuple([id:params.sample_id], file(params.assembly,checkIfExists:true))),
          Channel.value(file(params.refgraph,checkIfExists:true)),
          Channel.value(file(params.reflist,checkIfExists:true)),
          Channel.value(resource.call(params.installation)),
          Channel.value(resource.call(params.macsyfinder)), Channel.value(file("${moduleDir}/../../bin/run_copla_candidates.py", checkIfExists: true)))
}
