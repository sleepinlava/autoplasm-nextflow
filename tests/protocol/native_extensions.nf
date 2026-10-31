nextflow.enable.dsl=2
include { protocolAssets } from '../../lib/protocol_assets'
include { MOBMESS_SYSTEMS; SYSTEM_ABUNDANCE } from '../../modules/protocol/systems'
include { MOSTPLAS } from '../../modules/protocol/host_models'
include { PROTOCOL_EVOLUTION } from '../../modules/protocol/evolution'
include { PROTOCOL_STRAIN_PROFILE; PROTOCOL_STRAIN_COMPARE } from '../../modules/protocol/strain'
include { ANCOMBC2 } from '../../modules/cross_sample/ancombc2'
include { AMRFINDERPLUS_RUN as AMRFINDERPLUS } from '../../modules/nf-core/amrfinderplus/run/main'
include { PROTOCOL_ANNOTATION_PRODUCTS } from '../../modules/protocol/annotation'
include { resourceInput } from '../../lib/resource_inputs'
include { PROTOCOL_INPUT_AUDIT; PROTOCOL_HOST_FILTER; PROTOCOL_RETENTION } from '../../modules/protocol/input_audit'
include { FASTP } from '../../modules/nf-core/fastp/main'
include { BOWTIE2_BUILD as BOWTIE2_BUILD_HOST } from '../../modules/nf-core/bowtie2/build/main'
include { BOWTIE2_ALIGN as BOWTIE2_ALIGN_HOST } from '../../modules/nf-core/bowtie2/align/main'
include { MMSEQS_EASYCLUSTER as PROTOCOL_PROTEIN_FAMILIES } from '../../modules/nf-core/mmseqs/easycluster/main'
include { PROTOCOL_PAIRED_QUANTIFICATION } from '../../modules/protocol/paired_quantification'
workflow {
    def assets="${moduleDir}/../../bin"
    if (params.component == 'qc') {
        reads=Channel.value(tuple([id:'native_qc'],file("${params.fixture}/R1.fastq"),file("${params.fixture}/R2.fastq")))
        reference=Channel.value(tuple([id:'native_qc'],file("${params.fixture}/host.fasta")))
        PROTOCOL_INPUT_AUDIT(reads,protocolAssets(assets,'protocol_input_audit.py'))
        FASTP(reads.map { meta,r1,r2 -> tuple(meta,[r1,r2],[]) },false,false,false)
        BOWTIE2_BUILD_HOST(reference)
        BOWTIE2_ALIGN_HOST(FASTP.out.reads,BOWTIE2_BUILD_HOST.out.index,reference,true,false)
        PROTOCOL_HOST_FILTER(BOWTIE2_ALIGN_HOST.out.bam.join(reference))
        PROTOCOL_RETENTION(FASTP.out.json.join(PROTOCOL_HOST_FILTER.out.reads),protocolAssets(assets,'protocol_input_audit.py'))
    } else if (params.component == 'evolution') {
        PROTOCOL_EVOLUTION(file("${params.fixture}/annotations"),file("${params.fixture}/systems"),
            [file("${params.fixture}/proteins.faa")],protocolAssets(assets,'protocol_evolution.py'))
    } else if (params.component == 'protein_families') {
        PROTOCOL_PROTEIN_FAMILIES(Channel.value(tuple([id:'native_proteins'],file("${params.fixture}/proteins.faa"))))
    } else if (params.component == 'mobmess') {
        MOBMESS_SYSTEMS(file("${params.fixture}/catalogue"),[],protocolAssets(assets,'protocol_systems.py'))
        SYSTEM_ABUNDANCE(file("${params.fixture}/abundance.tsv"),MOBMESS_SYSTEMS.out.systems,protocolAssets(assets,'protocol_systems.py'))
    } else if (params.component == 'mostplas') {
        MOSTPLAS(file("${params.fixture}/catalogue"),[],file(params.mostplas_source),protocolAssets(assets,'mostplas_predict.py'))
    } else if (params.component == 'ancombc2') {
        ANCOMBC2(file("${params.fixture}/abundance.tsv"),file("${params.fixture}/metadata.tsv"),protocolAssets(assets,'ancombc2_plasmid.R'))
    } else if (params.component == 'amrfinderplus') {
        AMRFINDERPLUS(Channel.value(tuple([id:'native_amrfinder'],file("${params.fixture}/catalogue/plasmids.fasta"))),
            Channel.value(resourceInput(params.amrfinderplus_db)))
        AMRFINDERPLUS.out.database_identity.view { name,identity -> 'AMRFINDER_DATABASE_IDENTITY\t'+groovy.json.JsonOutput.toJson(identity) }
        PROTOCOL_ANNOTATION_PRODUCTS(file("${params.fixture}/catalogue"),file("${params.fixture}/systems"),file("${params.fixture}/abundance.tsv"),
            [],AMRFINDERPLUS.out.report.map { meta,path -> path }.toList(),[],[],[],[],[],protocolAssets(assets,'protocol_annotation.py'))
    } else if (params.component == 'strain') {
        ch_bams=Channel.fromPath("${params.fixture}/sample*.bam").map { bam -> tuple([id:bam.baseName],bam) }
        PROTOCOL_PAIRED_QUANTIFICATION(ch_bams,file("${params.fixture}/catalogue"),protocolAssets(assets,'protocol_quantification.py'))
        PROTOCOL_STRAIN_PROFILE(PROTOCOL_PAIRED_QUANTIFICATION.out.qualified_bam,file("${params.fixture}/catalogue"),file("${params.fixture}/mags"),protocolAssets(assets,'protocol_catalogue.py'))
        PROTOCOL_STRAIN_COMPARE(PROTOCOL_STRAIN_PROFILE.out.profile.map { meta,dir -> dir }.toList(),protocolAssets(assets,'protocol_catalogue.py'))
    }
}
