nextflow.enable.dsl=2
include { CROSS_SAMPLE } from '../../subworkflows/cross_sample'
include { reportSamples } from '../../lib/report_events'
workflow {
    root = params.fixture_dir
    ids = params.sample_ids
    contigs = Channel.of(file("${root}/contigs.tsv",checkIfExists:true))
    if (params.duplicate_contig_table) contigs = contigs.mix(contigs)
    states = params.omit_state ? Channel.empty() : Channel.of(file("${root}/states.tsv",checkIfExists:true))
    fasta = Channel.fromList(ids).map { sid -> tuple([id:sid],file("${root}/${sid}/plasmids.fasta",checkIfExists:true)) }
    consensus = Channel.fromList(ids).map { sid -> tuple([id:sid],file("${root}/${sid}/consensus.tsv",checkIfExists:true)) }
    structure = Channel.fromList(ids).map { sid -> tuple([id:sid],file("${root}/${sid}/structure.tsv",checkIfExists:true)) }
    events = reportSamples(fasta,'plasmid_fasta','controlled_detection')
        .mix(reportSamples(consensus,'consensus','controlled_detection'), reportSamples(structure,'structure','controlled_detection'))
    CROSS_SAMPLE(contigs,Channel.of(file("${root}/plasmids.tsv",checkIfExists:true)),states,Channel.empty(),events,ids.size(),2)
}
