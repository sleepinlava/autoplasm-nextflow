nextflow.enable.dsl=2
include { PROTOCOL_CATALOGUE } from '../../subworkflows/protocol_catalogue'
include { QUANTIFY_CATALOGUE } from '../../subworkflows/shared_quantification'
workflow {
    ch_rows=Channel.fromPath("${params.fixture}/sample*/assembly.fasta").map { assembly ->
        def folder=assembly.parent
        tuple([id:folder.name],assembly,folder.resolve('bins'),folder.resolve('summary.tsv'),folder.resolve('structure.tsv'))
    }
    PROTOCOL_CATALOGUE(ch_rows.map { meta,a,b,s,t -> tuple(meta,a) },
        ch_rows.map { meta,a,b,s,t -> tuple(meta,b,'fixture_native_bins') },
        ch_rows.map { meta,a,b,s,t -> tuple(meta,s) },ch_rows.map { meta,a,b,s,t -> tuple(meta,t) })
    ch_reads=ch_rows.map { meta,a,b,s,t -> tuple(meta,a.parent.resolve('R1.fastq'),a.parent.resolve('R2.fastq')) }
    QUANTIFY_CATALOGUE(PROTOCOL_CATALOGUE.out.catalogue.first(),ch_reads,Channel.empty(),'short',Channel.value([samples:['sample1','sample2','sample3']]))
}
