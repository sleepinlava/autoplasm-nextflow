nextflow.enable.dsl=2

include { DASTOOL_DASTOOL as DAS_TOOL } from '../../modules/nf-core/dastool/dastool/main'

workflow {
    inputs = Channel.of(tuple([id: 'DASToolRun1'],
        file(params.assembly, checkIfExists: true),
        params.predictions.collect { file(it, checkIfExists: true) }, []))
    DAS_TOOL(inputs, [])
    DAS_TOOL.out.bins.view { meta, bins -> "EXPORTED_BINS=${meta.id}:${bins}" }
}
