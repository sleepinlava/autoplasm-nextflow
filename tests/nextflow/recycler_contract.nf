// Controlled graph/metadata fixtures; native original preparation and consumer.
nextflow.enable.dsl = 2
include { RECYCLER_INPUTS } from '../../modules/binning/recycler_inputs'
include { RECYCLER } from '../../modules/binning/recycler'
workflow {
    def root = file(params.fixture_dir)
    def ids = params.ids.split(',') as List
    if (params.direct_bam) {
        RECYCLER(Channel.fromList(ids.collect { id -> tuple([id:id],
            file("${root}/${id}.fastg",checkIfExists:true),
            file("${root}/${id}.provenance.json",checkIfExists:true),
            file("${root}/${id}.bam",checkIfExists:true),
            file("${root}/${params.index_name ?: id + '.bam.bai'}",checkIfExists:true)) }), Channel.value(tuple(file("${moduleDir}/../../bin/validate_recycler_inputs.py", checkIfExists: true), file("${moduleDir}/../../bin/run_recycler_checked.py", checkIfExists: true))))
    } else {
        RECYCLER_INPUTS(Channel.fromList(ids.collect { id -> tuple([id:id],
            file("${root}/${id}.fastg",checkIfExists:true),
            file("${root}/${id}.provenance.json",checkIfExists:true),
            file("${root}/${id}_1.fq",checkIfExists:true),
            file("${root}/${id}_2.fq",checkIfExists:true)) }))
        RECYCLER(RECYCLER_INPUTS.out.bam, Channel.value(tuple(file("${moduleDir}/../../bin/validate_recycler_inputs.py", checkIfExists: true), file("${moduleDir}/../../bin/run_recycler_checked.py", checkIfExists: true))))
    }
}
