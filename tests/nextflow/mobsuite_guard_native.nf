nextflow.enable.dsl=2
include { resourceInput } from '../../lib/resource_inputs'
include { MOBSUITE_RECON as MOB_RECON } from '../../modules/nf-core/mobsuite/recon'
include { MOBSUITE_RECON as MOB_SUITE_ANNOT } from '../../modules/nf-core/mobsuite/recon'
include { MOBSUITE_TYPER as MOB_TYPER } from '../../modules/nf-core/mobsuite/typer'
workflow {
    def sequence=Channel.value(tuple([id:'bacterial_control'],file(params.fasta,checkIfExists:true)))
    def helper=Channel.value(file("${moduleDir}/../../bin/mobsuite_preflight.py",checkIfExists:true))
    if(params.mode=='typer') {
        MOB_TYPER(sequence,Channel.value(resourceInput(params.database)),[],[],[],[],[],[],[],false,false,helper)
    } else if(params.mode=='annotation') {
        MOB_SUITE_ANNOT(sequence,helper)
    } else {
        MOB_RECON(sequence,helper)
    }
}
