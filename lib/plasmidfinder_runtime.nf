/* Both script closures run before their task-cache lookup. */
def plasmidfinderRuntime(task, engine, meta) {
    def accelerator = task.accelerator
    return [conda: task.conda?.toString() ?: '', container: task.container?.toString() ?: '',
            engine: engine?.toString() ?: '',
            accelerator: accelerator ? [request: accelerator.request, limit: accelerator.limit,
                                         type: accelerator.type, runtime: accelerator.runtime] : null,
            before_script: task.beforeScript ?: '', modules: task.module ?: [],
            container_options: task.containerOptions ?: '', args: task.ext.args?.toString() ?: '',
            output_prefix: task.ext.prefix?.toString() ?: meta.id.toString()]
}

def plasmidfinderRequireRuntime(identity, actual) {
    if (identity.runtime != actual)
        throw new IllegalStateException('PlasmidFinder resource probe/consumer runtime mismatch before cache lookup; configure PLASMIDFINDER and PLASMIDFINDER_RESOURCE_PROBE with matching conda/container/accelerator/beforeScript/modules/containerOptions')
}

def plasmidfinderRuntimeBase64(value) {
    return groovy.json.JsonOutput.toJson(value).getBytes('UTF-8').encodeBase64().toString()
}

def plasmidfinderQuote(value) {
    return "'" + value.toString().replace("'", "'\"'\"'") + "'"
}

def plasmidfinderResourceRecord(meta, receipt) {
    return tuple(meta, new groovy.json.JsonSlurper().parseText(receipt.text), receipt)
}
