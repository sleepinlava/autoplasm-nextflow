include { PLASMID_CATALOG_PREPARE } from '../../modules/comparative/catalog_prepare'

workflow {
    PLASMID_CATALOG_PREPARE(params.contigs.collect { file(it, checkIfExists:true) },
        file(params.catalogue_builder, checkIfExists:true))
}
