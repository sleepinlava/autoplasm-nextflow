include { SHARED_CATALOGUE } from '../../modules/cross_sample/shared_catalogue'
workflow {
    SHARED_CATALOGUE(Channel.of(tuple(['s1', 's2'],
        [file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261028-shared-catalogue-provenance/in/assemblies/s1.fa'), file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261028-shared-catalogue-provenance/in/assemblies/s2.fa')],
        [file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261028-shared-catalogue-provenance/in/plasmids/s1.fa'), file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261028-shared-catalogue-provenance/in/plasmids/s2.fa')])),
        Channel.value(2),
        Channel.value(file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/bin/build_shared_catalogue.py', checkIfExists: true)))
    SHARED_CATALOGUE.out.cohort_provenance.view { it -> "PROV \${it[0]} cohort=\${it[5]}" }
}
