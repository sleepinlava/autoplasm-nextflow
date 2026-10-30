include { MULTIQC } from '../../modules/nf-core/multiqc/main'
workflow {
    input = Channel.of(tuple([id: 'multiqc-iface'], [file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261028-fastp-provenance-v3/work/3d/6d59bc5265b09784d490e9fd5c7e80/fastp-iface.fastp.json')], [], [], [], []))
    MULTIQC(input)
    MULTIQC.out.task_provenance.view { it -> "PROV \${it[0]} \${it[3]} sha=\${it[5]}" }
}
