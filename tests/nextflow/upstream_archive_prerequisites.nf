nextflow.enable.dsl=2
include { UNTAR as UNTAR_NESTED; UNTAR as UNTAR_FLAT } from '../nf-test/prerequisites/nf-core/untar/main'
include { GUNZIP } from '../nf-test/prerequisites/nf-core/gunzip/main'
include { PIGZ_COMPRESS } from '../nf-test/prerequisites/nf-core/pigz/compress/main'

workflow {
    GUNZIP(Channel.value(tuple([id:'decoded', group:'preserved'], file(params.gzip, checkIfExists:true))))
    GUNZIP.out.gunzip.view { meta, result -> "DECODED=${meta.id}:${meta.group}:${result}" }
    if (params.execute_other_tools) {
        PIGZ_COMPRESS(Channel.value(tuple([id:'compressed', group:'preserved'], file(params.fasta, checkIfExists:true))))
        UNTAR_NESTED(Channel.value(tuple([id:'nested', group:'preserved'], file(params.nested_archive, checkIfExists:true))))
        UNTAR_FLAT(Channel.value(tuple([id:'flat', group:'preserved'], file(params.flat_archive, checkIfExists:true))))
        PIGZ_COMPRESS.out.archive.view { meta, result -> "COMPRESSED=${meta.id}:${meta.group}:${result}" }
        UNTAR_NESTED.out.untar.view { meta, result -> "NESTED=${meta.id}:${meta.group}:${result}" }
        UNTAR_FLAT.out.untar.view { meta, result -> "FLAT=${meta.id}:${meta.group}:${result}" }
    }
}
