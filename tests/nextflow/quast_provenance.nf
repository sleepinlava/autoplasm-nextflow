include { QUAST } from '../../modules/nf-core/quast/main'
workflow {
    QUAST(Channel.of(tuple([id: 'q'], [file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261020-quast-real/pUTI89.fasta')])),
          Channel.value(tuple([:], [])), Channel.value(tuple([:], [])))
    QUAST.out.task_provenance.view { it -> "PROV ${it[0]} ${it[3]} sha=${it[5]}" }
}
