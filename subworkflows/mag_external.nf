/* Reuse the existing quality/taxonomy modules on PlasMAAG cellular bins. */
include { taggedResourceInput } from '../lib/resource_inputs'
include { selectedTools } from '../lib/tool_selection'
include { reportEvidence } from '../lib/report_events'
include { CHECKM2_PREDICT as CHECKM2 } from '../modules/nf-core/checkm2/predict/main'
include { GTDBTK_CLASSIFYWF as GTDBTK } from '../modules/nf-core/gtdbtk/classifywf/main'
workflow MAG_EXTERNAL {
    take:
    ch_bins
    main:
    ch_events=Channel.empty()
    ch_quality=Channel.empty()
    ch_taxonomy=Channel.empty()
    if (selectedTools(params.mag_tools).contains('checkm2')) {
        CHECKM2(ch_bins,Channel.value(taggedResourceInput([id:'checkm2_db'],params.checkm2_db)))
        ch_quality=CHECKM2.out.checkm2_tsv
        ch_events=ch_events.mix(reportEvidence([channels:CHECKM2.out],'07_host_prediction','CHECKM2'))
    }
    if (selectedTools(params.mag_tools).contains('gtdbtk')) {
        GTDBTK(ch_bins,Channel.value(taggedResourceInput([id:'gtdbtk_db'],params.gtdbtk_db)),false,
            Channel.value(file("${moduleDir}/../bin/normalize_gtdb_bins.py",checkIfExists:true)))
        ch_taxonomy=GTDBTK.out.summary
        ch_events=ch_events.mix(reportEvidence([channels:GTDBTK.out],'07_host_prediction','GTDBTK'))
    }
    emit:
    report_events=ch_events
    quality=ch_quality
    taxonomy=ch_taxonomy
}
