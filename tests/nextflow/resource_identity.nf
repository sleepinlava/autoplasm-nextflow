nextflow.enable.dsl=2

process READ_RESOURCE {
    cache 'deep'
    input:
    tuple path(resource), val(identity)
    output:
    tuple val(identity), path('observed.txt')
    script:
    """
    cat '${resource}/signal.txt' > observed.txt
    """
}

workflow {
    def ResourceIdentity = new GroovyClassLoader().parseClass(new File("${moduleDir}/../../lib/ResourceIdentity.groovy"))
    if (params.mode == 'properties') {
        Channel.fromList(params.cases).map { row ->
            try {
                def root = file(row.root,checkIfExists:true)
                def members = row.containsKey('members') ? row.members.collect { file(it,checkIfExists:true) } :
                    ResourceIdentity.members(root)
                ['case':row.id, identity:row.containsKey('members') ? ResourceIdentity.capture(root,members) : ResourceIdentity.capture(root)]
            } catch (Exception error) {
                ['case':row.id, error:error.class.simpleName, message:error.message]
            }
        }.view { row -> 'IDENTITY_CONTROL=' + groovy.json.JsonOutput.toJson(row) }
    } else {
        def root = file(params.resource,checkIfExists:true)
        def identity = ResourceIdentity.capture(root)
        READ_RESOURCE(Channel.value(tuple(root,identity)))
        READ_RESOURCE.out.view { actual, result -> 'CACHE_CONTROL=' + groovy.json.JsonOutput.toJson([identity:actual,observed:result.text]) }
    }
}
