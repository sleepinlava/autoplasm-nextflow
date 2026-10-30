include { FASTP } from '../../modules/nf-core/fastp/main'
workflow {
    FASTP(Channel.of(tuple([id: 'fastp-iface', single_end: false],
        [file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261027-ena-multi/ena/SRR19638267_1.fastq.gz'),
         file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261027-ena-multi/ena/SRR19638267_2.fastq.gz')],
        [])),
        false, false, false)
    FASTP.out.task_provenance.view { it -> "PROV ${it[0]} ${it[3]} sha=${it[5]}" }
}
