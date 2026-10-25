nextflow.enable.dsl=2
include { SPADES as METASPADES } from '../../modules/nf-core/spades/main'
workflow SPADES_BUNDLE {
    METASPADES(Channel.value(tuple([id:'fixture',single_end:false],[file(params.read1,checkIfExists:true),file(params.read2,checkIfExists:true)],[],[])),[],[],Channel.value(file("${moduleDir}/../../bin/spades_graph_provenance.py",checkIfExists:true)))
    METASPADES.out.plasmaag_assembly.view { meta,bundle -> "PLASMAAG_BUNDLE=${meta.id}:${bundle}" }
}
workflow { SPADES_BUNDLE() }
