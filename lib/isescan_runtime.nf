/* Both script closures run before their task-cache lookup. */
def isescanRuntime(task, engine, meta) {
    def accelerator = task.accelerator
    return [conda: task.conda?.toString() ?: '', container: task.container?.toString() ?: '',
            engine: engine?.toString() ?: '',
            accelerator: accelerator ? [request: accelerator.request, limit: accelerator.limit,
                                         type: accelerator.type, runtime: accelerator.runtime] : null,
            before_script: task.beforeScript ?: '', modules: task.module ?: [],
            container_options: task.containerOptions ?: '', output_prefix: "${meta.id}.isescan_out".toString()]
}

def isescanRequireRuntime(identity, actual) {
    if (identity.runtime != actual)
        throw new IllegalStateException('ISEScan resource probe/consumer runtime mismatch before cache lookup; configure ISESCAN and ISESCAN_RESOURCE_PROBE with matching conda/container/accelerator/beforeScript/modules/containerOptions')
}

def isescanRuntimeBase64(value) {
    return groovy.json.JsonOutput.toJson(value).getBytes('UTF-8').encodeBase64().toString()
}

def isescanQuote(value) {
    return "'" + value.toString().replace("'", "'\"'\"'") + "'"
}

def isescanResourceRecord(meta, receipt) {
    return tuple(meta, new groovy.json.JsonSlurper().parseText(receipt.text), receipt)
}
