include { GENOMAD_ENDTOEND as GENOMAD } from '../../modules/nf-core/genomad/endtoend/main'
workflow {
    GENOMAD(Channel.of(tuple([id: 'genomad-iface'], file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261020-quast-real/pUTI89.fasta'))),
            Channel.of(tuple([:], file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261027-ena-multi/databases/genomad_db'), 'subset-locked')))
    GENOMAD.out.task_provenance.view { it -> "PROV ${it[0]} ${it[3]} sha=${it[5]}" }
}
