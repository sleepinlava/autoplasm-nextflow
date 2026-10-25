nextflow.enable.dsl = 2

include { HOST_LINKING } from '../../subworkflows/host_linking'

workflow {
    def root = file(params.fixture_dir)
    def ids = ['S1', 'S2', 'S3', 'S4']
    if (params.empty_plasmids) {
        ch_plasmids = Channel.empty()
    } else if (params.duplicate_keys) {
        def duplicateMeta = [id: 'S1']
        def duplicateFasta = file("${root}/S1.plasmid_contigs.fasta", checkIfExists: true)
        ch_plasmids = Channel.of(tuple(duplicateMeta, duplicateFasta), tuple(duplicateMeta, duplicateFasta))
    } else {
        ch_plasmids = Channel.fromList(['S1', 'S2'].collect { id ->
            tuple([id: id], file("${root}/${id}.plasmid_contigs.fasta", checkIfExists: true))
        })
    }
    ch_assembly = Channel.empty()
    ch_longread_bam = Channel.empty()
    ch_plasmid_abundance = Channel.empty()
    ch_host_profile = Channel.empty()
    def magIds = params.duplicate_mag_keys ? ['S1', 'S1', 'S3'] : ['S1', 'S3']
    def taxonomyIds = params.duplicate_taxonomy_keys ? ['S1', 'S1', 'S4'] : ['S1', 'S4']
    ch_mag_bins = params.omit_mag ? Channel.empty() : Channel.fromList(magIds.collect { id ->
        tuple([id: id], file("${root}/${id}.metabat2_bins", checkIfExists: true))
    })
    ch_taxonomy = params.omit_taxonomy ? Channel.empty() : Channel.fromList(taxonomyIds.collect { id ->
        tuple([id: id], file("${root}/${id}.taxonomy.tsv", checkIfExists: true))
    })
    HOST_LINKING(ch_plasmids, ch_assembly, ch_longread_bam, ch_plasmid_abundance,
                 ch_host_profile, ch_mag_bins, ch_taxonomy, false)
    HOST_LINKING.out.links.view { "OPTIONAL_LINK\t${it}" }
}
