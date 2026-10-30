include { SPADES } from '../../modules/nf-core/spades/main'
workflow {
    SPADES(Channel.of(tuple([id: 'spades-iface', single_end: false],
        [file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261028-spades-provenance/test_minigut_R1.fastq.gz'),
         file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261028-spades-provenance/test_minigut_R2.fastq.gz')],
        [], [])),
        Channel.value([]), Channel.value([]), Channel.value(file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/bin/spades_graph_provenance.py', checkIfExists: true)))
    SPADES.out.task_provenance.view { it -> "PROV ${it[0]} ${it[3]} sha=${it[5]}" }
}
