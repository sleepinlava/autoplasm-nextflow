include { MOBSUITE_TYPER } from '../../modules/nf-core/mobsuite/typer/main'
include { MOBSUITE_RECON } from '../../modules/nf-core/mobsuite/recon/main'
include { resourceInput } from '../../lib/resource_inputs'

// Native prepared-resource integration check: production modules with the
// controlled 3.1.8 DB. Both modules receive the actual explicit directory
// identity. This does not cover the default environment database branch.
workflow {
    db = Channel.value(resourceInput(params.mobsuite_db))
    helper = Channel.value(file("${projectDir}/../../bin/mobsuite_preflight.py", checkIfExists: true))
    MOBSUITE_TYPER(
        Channel.of(tuple([id: 'typer-native'], file(params.mobsuite_typer_fasta, checkIfExists: true))),
        db,
        Channel.value([]), Channel.value([]), Channel.value([]),
        Channel.value([]), Channel.value([]), Channel.value([]),
        Channel.value([]), true, true, helper)
    MOBSUITE_RECON(
        Channel.of(tuple([id: 'recon-native'], file(params.mobsuite_recon_fasta, checkIfExists: true))),
        db,
        helper)
}
