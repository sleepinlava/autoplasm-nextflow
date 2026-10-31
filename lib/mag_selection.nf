include { selectedTools } from './tool_selection'

// One final bin set per sample: a single binner, or an explicitly selected
// DAS Tool aggregation. Keep this guard usable by direct subworkflow callers.
def magSelectionError(value) {
    def tools = selectedTools(value).unique()
    def allowed = ['plasmaag', 'metabat2', 'concoct', 'semibin', 'das_tool', 'checkm2', 'gtdbtk']
    def unknown = tools.findAll { !allowed.contains(it) }
    if (unknown) return "--mag_tools has unknown tools: ${unknown}"
    def binners = ['plasmaag', 'metabat2', 'concoct', 'semibin'].findAll { tools.contains(it) }
    if (tools.contains('plasmaag') && binners.size() > 1) return 'PlasMAAG cellular bins must be the sole MAG source'
    if (tools && !binners) return '--mag_tools requires at least one binner: plasmaag, metabat2, concoct or semibin'
    if (binners.size() > 1 && !tools.contains('das_tool')) {
        return 'Multiple MAG binners require explicitly selecting das_tool in --mag_tools'
    }
    return null
}
