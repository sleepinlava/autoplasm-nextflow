nextflow.enable.dsl=2
include { REPORTING } from '../../modules/cross_sample/report'
include { reportEvidence; reportSamples } from '../../lib/report_events'

process LATE_OPTIONAL {
    publishDir "${params.outdir}/08_annotation", enabled: false
    input:
    val fail_late
    output:
    path 'late.txt', emit: result
    tuple val('LATE_OPTIONAL'), val('controlled_delay'), val('not_a_biological_tool'), emit: versions_control
    script:
    """
    sleep 2
    ${fail_late ? 'echo deliberate-late-failure >&2; exit 7' : "printf 'declared current output\\n' > late.txt"}
    """
}

workflow {
    ids = ['S.1', '001']
    fasta = Channel.fromList(ids).map { sid -> tuple([id: sid], file("${params.fixture_dir}/${sid}/plasmids.fasta", checkIfExists: true)) }
    consensus = Channel.fromList(ids.reverse()).map { sid -> tuple([id: sid], file("${params.fixture_dir}/${sid}/consensus.tsv", checkIfExists: true)) }
    structure = Channel.fromList(ids).map { sid -> tuple([id: sid], file("${params.fixture_dir}/${sid}/structure.tsv", checkIfExists: true)) }
    events = reportSamples(fasta, 'plasmid_fasta', 'controlled_detection')
        .mix(reportSamples(consensus, 'consensus', 'controlled_detection'),
             reportSamples(structure, 'structure', 'controlled_structure'))
    if (params.run_late) {
        LATE_OPTIONAL(params.fail_late)
        events = events.mix(reportEvidence([channels: LATE_OPTIONAL.out], '08_annotation', 'LATE_OPTIONAL'))
    }
    REPORTING(events, file("${params.fixture_dir}/samples.tsv", checkIfExists: true),
              [platform: 'assembly', project_name: 'Explicit current inputs'])
}
