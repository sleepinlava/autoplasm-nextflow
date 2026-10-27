nextflow.enable.dsl=2
include { resourceInput; taggedResourceInput } from '../../lib/resource_inputs'
include { MOBSUITE_TYPER as MOB } from '../../modules/nf-core/mobsuite/typer/main'
include { BAKTA_BAKTA as BAKTA } from '../../modules/nf-core/bakta/bakta/main'
include { AMRFINDERPLUS_RUN as AMR } from '../../modules/nf-core/amrfinderplus/run/main'
include { RGI_MAIN as RGI } from '../../modules/nf-core/rgi/main/main'
include { EGGNOGMAPPER as EGG } from '../../modules/nf-core/eggnogmapper/main'
include { METAPHLAN_METAPHLAN as META } from '../../modules/nf-core/metaphlan/metaphlan/main'
include { KRAKEN2_KRAKEN2 as KRAKEN } from '../../modules/nf-core/kraken2/kraken2/main'
include { GTDBTK_CLASSIFYWF as GTDB } from '../../modules/nf-core/gtdbtk/classifywf/main'
include { CHECKM2_PREDICT as CHECK } from '../../modules/nf-core/checkm2/predict/main'
include { BLAST_BLASTN as BLAST } from '../../modules/nf-core/blast/blastn/main'
include { MACSYFINDER_SEARCH as MACSY } from '../../modules/nf-core/macsyfinder/search/main'
include { DASTOOL_DASTOOL as DAS } from '../../modules/nf-core/dastool/dastool/main'
include { PLASMIDHOSTFINDER as PHF } from '../../modules/host/plasmidhostfinder'

workflow {
    def fasta = file(params.fasta, checkIfExists: true)
    def sequence = Channel.value(tuple([id: 'CACHE_OBSERVER', single_end: true], fasta))
    def resource = { name -> Channel.value(resourceInput(params.resources[name])) }
    def tagged = { label, name -> Channel.value(taggedResourceInput(label, params.resources[name])) }
    MOB(sequence, resource.call('MOB_db'), [], [], [], [], [], [], [], false, false,Channel.value(file("${moduleDir}/../../bin/mobsuite_preflight.py",checkIfExists:true)))
    BAKTA(sequence, resource.call('BAKTA_db'), [], [], [], [])
    AMR(sequence, resource.call('AMR_db'))
    RGI(sequence, resource.call('RGI_card'), resource.call('RGI_wildcard'),
        Channel.value(file("${moduleDir}/../../bin/validate_rgi_card.py", checkIfExists: true)))
    EGG(sequence, tagged.call('diamond', 'EGG_db'), resource.call('EGG_data'))
    META(sequence, resource.call('META_db'), false)
    KRAKEN(sequence, resource.call('KRAKEN_db'), false, false)
    GTDB(sequence, tagged.call([id: 'CACHE_OBSERVER_DB'], 'GTDB_db'), false,
        Channel.value(file("${moduleDir}/../../bin/normalize_gtdb_bins.py", checkIfExists: true)))
    CHECK(sequence, tagged.call([id: 'CACHE_OBSERVER_DB'], 'CHECK_db'))
    BLAST(sequence, tagged.call([id: 'CACHE_OBSERVER_DB'], 'BLAST_db'), [], [], false)
    MACSY(Channel.value(tuple([id: 'CACHE_OBSERVER'], fasta, [])), resource.call('MACSY_models'), 'STUB_ONLY')
    DAS(Channel.value(tuple([id: 'CACHE_OBSERVER'], fasta,
        [file(params.bins, checkIfExists: true)], [])), resource.call('DAS_db'))
    PHF(sequence, resource.call('PHF_db'))
}
