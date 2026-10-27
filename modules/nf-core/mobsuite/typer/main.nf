include { mobsuiteQuote } from '../../../../lib/mobsuite_runtime'

process MOBSUITE_TYPER {
    cache 'deep'
    tag "${meta.id}"
    label 'process_low'

    conda "${moduleDir}/environment.yml"
    container "${workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container
        ? 'https://depot.galaxyproject.org/singularity/mob_suite:3.1.9--pyhdfd78af_0'
        : 'quay.io/biocontainers/mob_suite:3.1.9--pyhdfd78af_0'}"

    input:
    tuple val(meta), path(fasta)
    tuple path(db), val(db_identity)
    path plasmid_mash_db
    path plasmid_meta_txt
    path plasmid_replicons_fas
    path repetitive_mask_fas
    path plasmid_mob_faa
    path plasmid_mpf_faa
    path plasmid_orit_fas
    val generate_biomarker_report
    val generate_mge_report
    path(preflight_helper, stageAs: 'mobsuite_preflight.py')

    output:
    tuple val(meta), path("*.txt"), emit: report
    tuple val(meta), path("*_biomarker_report.txt"), optional: true, emit: biomarker_report
    tuple val(meta), path("*_mge_report.txt"), optional: true, emit: mge_report
    tuple val("${task.process}"), val('mobsuite'), eval("mob_typer --version | sed 's/mob_typer //g'"), topic: versions, emit: versions_mobsuite

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    def biomarker_report_cmd = generate_biomarker_report ? "--biomarker_report_file ${prefix}_biomarker_report.txt" : ''
    def mge_report_cmd = generate_mge_report ? "--mge_report_file ${prefix}_mge_report.txt" : ''
    def plasmid_mash_db_cmd = plasmid_mash_db ? "--plasmid_mash_db ${mobsuiteQuote(plasmid_mash_db)}" : ''
    def plasmid_meta_cmd = plasmid_meta_txt ? "--plasmid_meta ${mobsuiteQuote(plasmid_meta_txt)}" : ''
    def plasmid_replicons_cmd = plasmid_replicons_fas ? "--plasmid_replicons ${mobsuiteQuote(plasmid_replicons_fas)}" : ''
    def repetitive_mask_cmd = repetitive_mask_fas ? "--repetitive_mask ${mobsuiteQuote(repetitive_mask_fas)}" : ''
    def plasmid_mob_cmd = plasmid_mob_faa ? "--plasmid_mob ${mobsuiteQuote(plasmid_mob_faa)}" : ''
    def plasmid_mpf_cmd = plasmid_mpf_faa ? "--plasmid_mpf ${mobsuiteQuote(plasmid_mpf_faa)}" : ''
    def plasmid_orit_fas_cmd = plasmid_orit_fas ? "--plasmid_orit ${mobsuiteQuote(plasmid_orit_fas)}" : ''
    def db_cmd = db ? "--database_directory ${mobsuiteQuote(db)}" : ''
    """
    python3 mobsuite_preflight.py --tool mob_typer --output mobsuite_preflight.json --execute -- \\
        --num_threads ${task.cpus} \\
        --sample_id ${mobsuiteQuote(prefix)} \\
        ${args} \\
        --infile ${mobsuiteQuote(fasta)} \\
        ${plasmid_mash_db_cmd} \\
        ${plasmid_meta_cmd} \\
        ${plasmid_replicons_cmd} \\
        ${repetitive_mask_cmd} \\
        ${plasmid_mob_cmd} \\
        ${plasmid_mpf_cmd} \\
        ${plasmid_orit_fas_cmd} \\
        ${db_cmd} \\
        --out_file ${prefix}.txt \\
        ${biomarker_report_cmd} \\
        ${mge_report_cmd}

    """

    stub:
    def args = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    echo ${args}

    touch ${prefix}.txt
    touch ${prefix}_biomarker_report.txt
    touch ${prefix}_mge_report.txt
    """
}
