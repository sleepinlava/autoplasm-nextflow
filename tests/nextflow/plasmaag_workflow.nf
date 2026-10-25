nextflow.enable.dsl=2
include { PLASMAAG_BINNING } from '../../subworkflows/plasmaag_binning'
workflow {
    // Copy ConfigMap records and never use Groovy Map.get(key, default), which inserts missing keys.
    def records = params.records.collect { new LinkedHashMap(it) }
    assemblies = Channel.fromList(records).map { row -> tuple([id:row.id, group:row.group], file(row.fasta,checkIfExists:true)) }
    reads = Channel.fromList(records.findAll { it.reads }).map { row -> tuple([id:row.getOrDefault('read_id',row.id), group:row.getOrDefault('read_group',row.group)], file(row.reads[0],checkIfExists:true), file(row.reads[1],checkIfExists:true)) }
    bundles = Channel.fromList(records.findAll { it.bundle }).map { row -> tuple([id:row.getOrDefault('bundle_id',row.id), group:row.getOrDefault('bundle_group',row.group)], file(row.bundle,checkIfExists:true)) }
    PLASMAAG_BINNING(assemblies,reads,bundles)
    PLASMAAG_BINNING.out.bins.view { meta,directory,state -> "PLASMAAG_SAMPLE=${meta.id}:${meta.group}:${state}:${directory}" }
}
