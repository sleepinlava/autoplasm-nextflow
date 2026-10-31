include { protocolAssets } from '../../lib/protocol_assets'
nextflow.enable.dsl=2
include { PROTOCOL_HOST_MATRIX; PROTOCOL_HOST_FASTSPAR; PROTOCOL_HOST_EDGES } from '../../modules/protocol/mag_association'
workflow {
    PROTOCOL_HOST_MATRIX(file("${params.fixture}/plasmids.tsv"),file("${params.fixture}/mags"),file("${params.fixture}/metadata.tsv"), protocolAssets("${moduleDir}/../../bin",'protocol_hosts.py'))
    ch_inputs=PROTOCOL_HOST_MATRIX.out.matrices.flatMap { dir -> dir.listFiles().findAll { it.name.endsWith('.tsv') }.collect { tuple([id:it.baseName],it) } }
    PROTOCOL_HOST_FASTSPAR(ch_inputs)
    PROTOCOL_HOST_EDGES(PROTOCOL_HOST_FASTSPAR.out.association, protocolAssets("${moduleDir}/../../bin",'protocol_hosts.py'))
}
