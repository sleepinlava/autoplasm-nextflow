/* Capture declared resource bytes before the consumer's task-cache lookup.
 * Empty optional resources stay explicit; no glob or per-file staging.
 */
def resourceInput(location) {
    if (location == null || (location instanceof Collection && location.isEmpty()))
        return tuple([], [schema_version: 2, resource_state: 'absent'])
    def root = file(location, checkIfExists: true, glob: false)
    def identity = new GroovyClassLoader().parseClass(new File("${moduleDir}/ResourceIdentity.groovy"))
    return tuple(root, identity.capture(root))
}

def taggedResourceInput(label, location) {
    def resource = resourceInput(location)
    return tuple(label, resource[0], resource[1])
}
