/* Evaluated in both process script closures, before consumer cache lookup. */
def semibinRuntime(task, engine, meta) {
    def accelerator = task.accelerator
    return [
        conda: task.conda?.toString() ?: '',
        container: task.container?.toString() ?: '',
        engine: engine?.toString() ?: '',
        accelerator: accelerator ? [request: accelerator.request, limit: accelerator.limit,
                                     type: accelerator.type, runtime: accelerator.runtime] : null,
        before_script: task.beforeScript ?: '',
        modules: task.module ?: [],
        container_options: task.containerOptions ?: '',
        args: (task.ext.args ?: '').toString(),
        args2: (task.ext.args2 ?: '').toString(),
        prefix: (task.ext.prefix ?: meta.id).toString()
    ]
}

def semibinRequireRuntime(identity, actual) {
    if (identity.runtime != actual)
        throw new IllegalStateException('SemiBin resource probe/consumer runtime mismatch before cache lookup; configure SEMIBIN and SEMIBIN_RESOURCE_PROBE with matching conda/container/accelerator, beforeScript, modules, containerOptions and ext.args/args2/prefix')
}

def semibinRuntimeBase64(runtime) {
    return groovy.json.JsonOutput.toJson(runtime).getBytes('UTF-8').encodeBase64().toString()
}

def semibinResourceRecord(meta, receipt) {
    def identity = new groovy.json.JsonSlurper().parseText(receipt.text)
    return tuple(meta, identity, receipt)
}
