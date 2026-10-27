/* Both script closures run before their task-cache lookup. */
def integronfinderRuntime(task, engine, meta) {
    def accelerator = task.accelerator
    return [conda: task.conda?.toString() ?: '', container: task.container?.toString() ?: '',
            engine: engine?.toString() ?: '',
            accelerator: accelerator ? [request: accelerator.request, limit: accelerator.limit,
                                         type: accelerator.type, runtime: accelerator.runtime] : null,
            before_script: task.beforeScript ?: '', modules: task.module ?: [],
            container_options: task.containerOptions ?: '', args: task.ext.args?.toString() ?: '',
            output_prefix: task.ext.prefix?.toString() ?: meta.id.toString()]
}

def integronfinderRequireRuntime(identity, actual) {
    if (identity.runtime != actual)
        throw new IllegalStateException('IntegronFinder resource probe/consumer runtime mismatch before cache lookup; configure INTEGRONFINDER and INTEGRONFINDER_RESOURCE_PROBE with matching conda/container/accelerator/beforeScript/modules/containerOptions')
}

def integronfinderRuntimeBase64(value) {
    return groovy.json.JsonOutput.toJson(value).getBytes('UTF-8').encodeBase64().toString()
}

def integronfinderQuote(value) {
    return "'" + value.toString().replace("'", "'\"'\"'") + "'"
}

def integronfinderResourceRecord(meta, receipt) {
    return tuple(meta, new groovy.json.JsonSlurper().parseText(receipt.text), receipt)
}
