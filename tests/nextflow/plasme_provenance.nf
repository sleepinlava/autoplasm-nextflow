include { PLASME } from '../../modules/detection/plasme'
workflow {
    PLASME(Channel.of(tuple([id: 'plasme-iface'], file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261020-quast-real/pUTI89.fasta'))),
           Channel.of(tuple(file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/runtime/plasme-DB-8046934/DB'), 'retained-db')),
           Channel.of(tuple(file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/runtime/PLASMe-4405d5aa'), 'retained-source')),
           Channel.of(tuple(file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/bin/normalize_plasme_outputs.py', checkIfExists: true), file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/bin/plasme_runtime.py', checkIfExists: true))))
    PLASME.out.task_provenance.view { it -> "PROV ${it[0]} ${it[3]} sha=${it[5]}" }
}
