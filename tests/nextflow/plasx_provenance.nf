include { PLASX } from '../../modules/detection/plasx'
workflow {
    PLASX(Channel.of(tuple([id: 'S.1'],
        file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261026-resource-consumers/plasx-native-v3/work/9b/73474e2db8b2649e1be567979eb391/S.1.contigs.fasta'), file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261026-resource-consumers/plasx-native-v3/work/9b/73474e2db8b2649e1be567979eb391/S.1.id_map.tsv'),
        file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261026-resource-consumers/plasx-native-v3/work/9b/73474e2db8b2649e1be567979eb391/S.1.gene_calls.tsv'), file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261026-resource-consumers/plasx-native-v3/work/9b/73474e2db8b2649e1be567979eb391/S.1.cogs_pfams.tsv'))),
        Channel.of(tuple(file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261024-plasx-native/primary'), 'retained-source')),
        Channel.of(tuple(file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261024-plasx-native/profiles'), 'retained-profiles')),
        Channel.value(file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261024-plasx-native/PlasX_coefficients_and_gene_enrichments.txt')),
        Channel.of(tuple(file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/bin/plasx_inputs.py', checkIfExists: true), file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/bin/plasx_checked.py', checkIfExists: true))))
    PLASX.out.task_provenance.view { it -> "PROV ${it[0]} ${it[3]} sha=${it[5]}" }
}
