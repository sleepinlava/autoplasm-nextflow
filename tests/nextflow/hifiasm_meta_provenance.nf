include { HIFIASM_META } from '../../modules/assembly/hifiasm_meta'
workflow {
    HIFIASM_META(Channel.of(tuple([id: 'hifiasm-iface'], file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261028-flye-provenance/interface-control-20000reads.fastq.gz'))))
    HIFIASM_META.out.task_provenance.view { it -> "PROV ${it[0]} ${it[3]} sha=${it[5]}" }
}
