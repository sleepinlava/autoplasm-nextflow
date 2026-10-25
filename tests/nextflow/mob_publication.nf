nextflow.enable.dsl=2
include { MOBSUITE_RECON as MOB_SUITE_ANNOT } from '../../modules/nf-core/mobsuite/recon'
include { MOBSUITE_RECON as MOB_RECON } from '../../modules/nf-core/mobsuite/recon'

workflow {
    records = Channel.fromList(params.records).map { row ->
        tuple([id: row.id, observer_empty: row.empty], file(row.fasta, checkIfExists: true))
    }
    MOB_SUITE_ANNOT(records)
    MOB_RECON(records)
    MOB_SUITE_ANNOT.out.contig_report.view { meta, report -> "ANNOT_REPORT=${meta.id}" }
    MOB_RECON.out.contig_report.view { meta, report -> "RECON_REPORT=${meta.id}" }
}
