// Audit-only candidate probe. Production still lacks context agreement and
// pre-execution revalidation; do not infer production closure from this harness.
include { MOBSUITE_TYPER } from '../../modules/nf-core/mobsuite/typer/main'
include { MOBSUITE_RECON } from '../../modules/nf-core/mobsuite/recon/main'

process MOB_RESOURCE_AUDIT_PROBE {
    cache false
    input:
    tuple val(meta), path(fasta)
    path helpers
    output:
    tuple val(meta), path('identity.json'), emit: identity
    script:
    def output = meta.tool == 'mob_typer' ? "--out_file ${meta.id}.txt" : '--outdir results'
    """
    python3 mobsuite_runtime_resources.py --tool ${meta.tool} --output identity.json -- \\
        --infile ${fasta} --sample_id ${meta.id} --num_threads ${task.cpus} ${output}
    """
}

workflow {
    inputs = Channel.of(
        tuple([id:'typer-native',tool:'mob_typer'], file(params.fasta,checkIfExists:true)),
        tuple([id:'recon-native',tool:'mob_recon'], file(params.fasta,checkIfExists:true)))
    helper = Channel.value(file("${projectDir}/../../bin/mobsuite_preflight.py",checkIfExists:true))
    identities = null
    if (params.probe?.toString() == 'true') {
        helpers = Channel.value(['mobsuite_preflight.py','mobsuite_runtime_resources.py'].collect {
            file("${projectDir}/../../bin/${it}",checkIfExists:true)
        })
        MOB_RESOURCE_AUDIT_PROBE(inputs,helpers)
        identities = MOB_RESOURCE_AUDIT_PROBE.out.identity.map { meta,receipt ->
            tuple(meta,[],new groovy.json.JsonSlurper().parseText(receipt.text))
        }
    } else {
        identities = inputs.map { meta,fasta -> tuple(meta,[],[schema_version:2,resource_state:'absent']) }
    }
    MOBSUITE_TYPER(inputs.filter { meta,fasta -> meta.tool == 'mob_typer' },
        identities.filter { meta,db,identity -> meta.tool == 'mob_typer' }.map { meta,db,identity -> tuple(db,identity) },
        Channel.value([]),Channel.value([]),Channel.value([]),Channel.value([]),
        Channel.value([]),Channel.value([]),Channel.value([]),false,false,helper)
    MOBSUITE_RECON(inputs.filter { meta,fasta -> meta.tool == 'mob_recon' },
        identities.filter { meta,db,identity -> meta.tool == 'mob_recon' }.map { meta,db,identity -> tuple(db,identity) },helper)
}
