include { MEGAHIT } from '../../modules/nf-core/megahit/main'
workflow {
    MEGAHIT(Channel.of(tuple([id: 'megahit-iface', single_end: false],
        [file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261027-ena-multi/ena/SRR19638267_1.fastq.gz')],
        [file('/home/sleepinlava/Projects/vibe_coding/trash_vibe_project/autoplasm-nextflow/results/tool-audit/20261027-ena-multi/ena/SRR19638267_2.fastq.gz')])))
    MEGAHIT.out.task_provenance.view { it -> "PROV ${it[0]} ${it[3]} sha=${it[5]}" }
}
