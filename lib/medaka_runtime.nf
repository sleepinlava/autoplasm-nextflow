def medakaRuntime(task, engine, meta) {
    def accelerator = task.accelerator
    return [conda: task.conda?.toString() ?: '', container: task.container?.toString() ?: '',
            engine: engine?.toString() ?: '',
            accelerator: accelerator ? [request: accelerator.request, limit: accelerator.limit,
                                         type: accelerator.type, runtime: accelerator.runtime] : null,
            before_script: task.beforeScript ?: '', modules: task.module ?: [],
            container_options: task.containerOptions ?: '', args: task.ext.args?.toString() ?: '',
            output_prefix: task.ext.prefix?.toString() ?: meta.id.toString()]
}

def medakaRequireRuntime(identity, actual) {
    if (identity.runtime != actual)
        throw new IllegalStateException('Medaka resource probe/consumer runtime mismatch before cache lookup; configure MEDAKA and MEDAKA_RESOURCE_PROBE with matching conda/container/accelerator/beforeScript/modules/containerOptions/args/prefix')
}

def medakaRuntimeBase64(value) {
    return groovy.json.JsonOutput.toJson(value).getBytes('UTF-8').encodeBase64().toString()
}

def medakaQuote(value) {
    return "'" + value.toString().replace("'", "'\"'\"'") + "'"
}

def medakaResourceRecord(meta, receipt) {
    return tuple(meta, new groovy.json.JsonSlurper().parseText(receipt.text), receipt)
}
