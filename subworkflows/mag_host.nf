/*
 * MAG host-genome subworkflow (DAG category mag_host_genomes): MetaBAT2 /
 * CONCOCT / SemiBin binners, optional DAS Tool aggregation, CheckM2 quality,
 * GTDB-Tk taxonomy. All optional via params.mag_tools.
 */
include { METABAT2 } from '../modules/mag/metabat2'
include { CONCOCT } from '../modules/mag/concoct'
include { SEMIBIN } from '../modules/mag/semibin'
include { DAS_TOOL } from '../modules/mag/das_tool'
include { CHECKM2 } from '../modules/mag/checkm2'
include { GTDBTK } from '../modules/mag/gtdbtk'

workflow MAG_HOST {
    take:
    ch_assembly     // tuple(meta, fasta)
    ch_contig_bam   // tuple(meta, bam)
    ch_contig_table // tuple(meta, coverm tsv)

    main:
    ch_metabat2 = Channel.empty()
    if (params.mag_tools.contains('metabat2')) {
        METABAT2(ch_assembly.join(ch_contig_bam))
        ch_metabat2 = METABAT2.out.bins
    }
    ch_concoct = Channel.empty()
    if (params.mag_tools.contains('concoct')) {
        CONCOCT(ch_assembly.join(ch_contig_table))
        ch_concoct = CONCOCT.out.output_dir
    }
    if (params.mag_tools.contains('semibin')) {
        SEMIBIN(ch_assembly.join(ch_contig_bam))
    }

    ch_final_bins = ch_metabat2
    if (params.mag_tools.contains('das_tool')) {
        ch_das_in = ch_assembly
            .join(ch_metabat2, remainder: true)
            .join(ch_concoct, remainder: true)
            .map { meta, asm, mb, cc -> tuple(meta, asm, [mb, cc].findAll { it != null }) }
            .filter { meta, asm, dirs -> !dirs.isEmpty() }
        DAS_TOOL(ch_das_in)
        ch_final_bins = DAS_TOOL.out.output_dir
    }

    if (params.mag_tools.contains('checkm2')) {
        CHECKM2(ch_final_bins)
    }
    ch_taxonomy = Channel.empty()
    if (params.mag_tools.contains('gtdbtk')) {
        GTDBTK(ch_final_bins, Channel.value(file(params.gtdbtk_db, checkIfExists: true)))
        ch_taxonomy = GTDBTK.out.taxonomy
    }

    emit:
    mag_bins = ch_final_bins  // tuple(meta, dir); may be empty
    taxonomy = ch_taxonomy    // tuple(meta, tsv); may be empty
}
