nextflow.enable.dsl=2
include { SHORT_READ_PROTOCOL } from '../../subworkflows/short_read_protocol'

workflow {
    ch_rows=Channel.fromPath("${params.fixture}/sample*/assembly.fasta").map { assembly ->
        def folder=assembly.parent
        tuple([id:folder.name],assembly,folder.resolve('bins'),folder.resolve('summary.tsv'),folder.resolve('structure.tsv'))
    }
    SHORT_READ_PROTOCOL(ch_rows.map { meta,a,b,s,t -> tuple(meta,a) },
        ch_rows.map { meta,a,b,s,t -> tuple(meta,a.parent.resolve('R1.fastq'),a.parent.resolve('R2.fastq')) },
        ch_rows.map { meta,a,b,s,t -> tuple(meta,b,'fixture_empty_bins') },
        ch_rows.map { meta,a,b,s,t -> tuple(meta,s) },ch_rows.map { meta,a,b,s,t -> tuple(meta,t) },Channel.empty(),Channel.empty())
}
