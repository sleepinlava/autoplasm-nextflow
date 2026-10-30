include { DIVERSITY } from '../../modules/cross_sample/diversity'
workflow {
    DIVERSITY(Channel.value(file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261028-diversity-provenance/in/abundance.tsv')),
              Channel.value(file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261028-diversity-provenance/in/metadata.tsv')),
              Channel.value(['diversity.R', 'statistics_input_contract.R'].collect { file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/bin/' + it, checkIfExists: true) }))
    DIVERSITY.out.cohort_provenance.view { it -> "PROV ${it[0]} cohort=${it[5]}" }
}
