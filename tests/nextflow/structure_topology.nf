nextflow.enable.dsl=2

include { PLASMID_STRUCTURE } from '../../modules/detection/structure'
include { REPORTING } from '../../modules/cross_sample/report'

workflow {
    if (params.report_only) {
        ids = ['SCP1', 'pUTI89', 'metadata_circle', 'mixed', 'empty']
        events = Channel.fromList(ids).flatMap { sid ->
            [['plasmid_fasta', "${params.fixture_dir}/${sid}.fasta"],
             ['consensus', "${params.outdir}/04_plasmid_detection/consensus/${sid}.plasmid_consensus.tsv"],
             ['structure', "${params.outdir}/04_plasmid_detection/structure/${sid}.plasmid_structure.tsv"]].collect { kind, path ->
                tuple([section:'04_plasmid_detection', producer:'controlled_completed_inputs', kind:kind, sample_id:sid], [file(path, checkIfExists:true)])
            }
        }
        REPORTING(events, file("${params.fixture_dir}/samples.tsv", checkIfExists:true), [platform:'assembly', project_name:params.project_name])
    } else {
        inputs = Channel.fromList(['SCP1', 'pUTI89', 'metadata_circle', 'mixed', 'empty'])
            .map { sid -> tuple([id: sid], file("${params.fixture_dir}/${sid}.fasta", checkIfExists: true)) }
        PLASMID_STRUCTURE(inputs)
    }
}
