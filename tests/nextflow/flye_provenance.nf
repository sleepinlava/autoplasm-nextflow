include { FLYE } from '../../modules/nf-core/flye/main'
workflow {
    FLYE(Channel.of(tuple([id: 'flye-iface'], file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261028-flye-provenance/interface-control-20000reads.fastq.gz'))), '--nano-raw')
    FLYE.out.task_provenance.view { it -> "PROV ${it[0]} ${it[3]} sha=${it[5]}" }
}
