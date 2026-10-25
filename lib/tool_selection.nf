// Pure normalization at each consumer: module params are copied by Nextflow.
// Name/type validation belongs to the main entry registry before task submission.
def selectedTools(value) {
    if (value == null) return []
    if (value instanceof List) return value.collect { it.toString().trim() }
    return value.toString().trim() ? value.toString().split(',', -1).collect { it.trim() } : []
}
