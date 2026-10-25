nextflow.enable.dsl=2

include { MAG_HOST } from '../../subworkflows/mag_host'

workflow {
    assemblies = Channel.fromList(params.records).map { row ->
        tuple([id: row.id, group: row.group], file(row.fasta, checkIfExists: true))
    }
    bams = Channel.fromList(params.records.reverse()).map { row ->
        tuple([id: row.id, group: row.group], file(row.bam, checkIfExists: true))
    }
    MAG_HOST(assemblies, bams, Channel.empty())
    MAG_HOST.out.mag_bins.view { meta, bins -> "FINAL_BINS=${meta.id}:${meta.group}:${bins}" }
}
