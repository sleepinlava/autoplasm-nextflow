include { FILTLONG } from '../../modules/nf-core/filtlong/main'
workflow {
    FILTLONG(Channel.of(tuple([id: 'filtlong-iface', single_end: true],
        [],
        file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261028-flye-provenance/interface-control-20000reads.fastq.gz'))))
    FILTLONG.out.task_provenance.view { it -> "PROV ${it[0]} ${it[3]} sha=${it[5]}" }
}
