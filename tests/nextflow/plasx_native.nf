nextflow.enable.dsl=2
include { PLASX_ANNOTATE; PLASX } from '../../modules/detection/plasx'

workflow ANNOTATE_ONLY {
    def resource = { location -> Channel.value(tuple(file(location, checkIfExists: true),
        files("${location}/**", type: 'file', hidden: true))) }
    ch_assembly = Channel.of(tuple([id: params.sample_id], file(params.assembly, checkIfExists: true)))
    PLASX_ANNOTATE(ch_assembly, resource.call(params.plasx_anvio_source), resource.call(params.plasx_cog_db), resource.call(params.plasx_pfam_db), Channel.value(tuple(file("${moduleDir}/../../bin/plasx_inputs.py", checkIfExists: true), file("${moduleDir}/../../bin/anvio_checked.py", checkIfExists: true))))
}

workflow {
    def resource = { location -> Channel.value(tuple(file(location, checkIfExists: true),
        files("${location}/**", type: 'file', hidden: true))) }
    if (params.annotation_only) {
        ANNOTATE_ONLY()
    } else {
        ch_assembly = Channel.of(tuple([id: params.sample_id], file(params.assembly, checkIfExists: true)))
        PLASX_ANNOTATE(ch_assembly, resource.call(params.plasx_anvio_source), resource.call(params.plasx_cog_db), resource.call(params.plasx_pfam_db), Channel.value(tuple(file("${moduleDir}/../../bin/plasx_inputs.py", checkIfExists: true), file("${moduleDir}/../../bin/anvio_checked.py", checkIfExists: true))))
        PLASX(PLASX_ANNOTATE.out.annotations, resource.call(params.plasx_source), resource.call(params.plasx_profiles),
            Channel.value(file(params.plasx_model, checkIfExists: true)), Channel.value(tuple(file("${moduleDir}/../../bin/plasx_inputs.py", checkIfExists: true), file("${moduleDir}/../../bin/plasx_checked.py", checkIfExists: true))))
    }
}
