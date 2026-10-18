// Real adjacent Streptomyces coelicolor chromosome regions feeding CLINKER.
// The pinned gbk pair (antiSMASH regions of NC_003888.3) carries .gbk
// extensions while CLINKER globs bakta_dir/*.gbff; the staging scaffolding
// copies the two real GenBank records under their .gbff names.
nextflow.enable.dsl = 2

include { CLINKER } from '../../../modules/comparative/clinker'

process STAGE_GBFF {
    // Test scaffolding: rename extension only, content stays the real
    // GenBank records (host coreutils, no container needed).
    label 'process_low'

    input:
    path(gbk_dir)

    output:
    path('bakta_gbff', type: 'dir')

    script:
    """
    mkdir bakta_gbff
    for f in ${gbk_dir}/*.gbk; do
        base=\$(basename "\$f" .gbk)
        cp "\$f" "bakta_gbff/\${base}.gbff"
    done
    """
}

workflow {
    def root = params.test_data
    def gbk_dir = file("${root}/gbk/streptomyces_coelicolor/dataset_1/NC_003888.3", checkIfExists: true)

    STAGE_GBFF(gbk_dir)
    CLINKER(STAGE_GBFF.out.map { dir -> [[id: 'sc_coelicolor_regions'], dir] })
}
