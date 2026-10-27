// P3 real-data chain: build a small BLAST database from the real pUTI89
// plasmid (makeblastdb, scaffold) and query it with the vendored BLAST_BLASTN
// node. The vendored blast/blastn suite is blocked by the unvendored
// blast/makeblastdb setup module; this chain covers the same node for real.
// Backend: podman (wave blast image, pulled on demand).
nextflow.enable.dsl = 2
include { resourceInput; taggedResourceInput } from '../../../lib/resource_inputs'

include { BLAST_BLASTN } from '../../../modules/nf-core/blast/blastn/main'

process MAKEBLASTDB_SCAFFOLD {
    // Test scaffolding (not a pipeline node): vendored blast/makeblastdb is
    // not in this repo, so build the tiny DB inline with the same image.
    label 'process_low'
    container 'community.wave.seqera.io/library/blast:2.17.0--d4fb881691596759'
    input:
    tuple val(meta), path(fasta)
    output:
    tuple val(meta), path("db", type: 'dir')
    script:
    """
    mkdir db
    makeblastdb -in ${fasta} -dbtype nucl -out db/pUTI89
    """
}

workflow {
    def asm = file("${params.test_data}/pUTI89.fasta", checkIfExists: true)
    MAKEBLASTDB_SCAFFOLD(Channel.of(tuple([id: 'mini_blast_db'], asm)))
    BLAST_BLASTN(Channel.of(tuple([id: 'pUTI89'], asm)),
        MAKEBLASTDB_SCAFFOLD.out.map { meta, db -> taggedResourceInput(meta, db) }, [], [], false)
}
