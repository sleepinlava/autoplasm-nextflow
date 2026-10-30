include { NANOPLOT } from '../../modules/nf-core/nanoplot/main'
workflow {
    NANOPLOT(Channel.of(tuple([id: 'nanoplot-iface'], file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261028-flye-provenance/interface-control-20000reads.fastq.gz'))))
    NANOPLOT.out.task_provenance.view { it -> "PROV ${it[0]} ${it[3]} sha=${it[5]}" }
}
