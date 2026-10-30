include { PLATON } from '../../modules/detection/platon'
workflow {
    PLATON(Channel.of(tuple([id: 'platon-iface'], file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261020-quast-real/pUTI89.fasta'))),
           Channel.of(tuple(file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261024-platon-native/database/db'), 'retained-1.7-db')),
           Channel.value(file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/bin/platon_checked.py', checkIfExists: true)))
    PLATON.out.task_provenance.view { it -> "PROV ${it[0]} ${it[3]} sha=${it[5]}" }
}
