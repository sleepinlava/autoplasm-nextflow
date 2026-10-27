/* Current-run files are path inputs. publishDir is only an output sink. */
process REPORT {
    cache 'deep'
    tag 'report'
    label 'process_single'
    conda "${moduleDir}/../../envs/r_analysis.yml"
    container 'autoplasm-r-analysis:latest'
    publishDir "${params.outdir}/report", mode: params.publish_dir_mode

    input:
    tuple val(records), path(report_files, stageAs: 'inputs????/*')
    path samplesheet, stageAs: 'run_samplesheet.tsv'
    path report_template, stageAs: 'report_template.Rmd'
    path reporter, stageAs: 'generate_report.R'
    val settings

    output:
    path 'report.md', emit: report_md
    path 'report.html', emit: report_html
    path 'methods.md', emit: methods_md
    path 'report_data.json', emit: data_json
    path 'report_inputs.json', emit: inputs_json

    script:
    def paths = report_files instanceof List ? report_files : [report_files]
    def manifest = [schema_version: 1, settings: settings, records: records.collect { record ->
        record.findAll { key, value -> key != 'file_indices' } +
            [files: (record.file_indices ?: []).collect { index -> paths[index].toString() }]
    }]
    def json = groovy.json.JsonOutput.prettyPrint(groovy.json.JsonOutput.toJson(manifest))
    """
cat > report_inputs.json <<'AUTOPLASM_REPORT_INPUTS_JSON'
${json}
AUTOPLASM_REPORT_INPUTS_JSON
Rscript ${reporter} \\
    --manifest report_inputs.json --samplesheet ${samplesheet} \\
    --template ${report_template} --out-prefix .
    """
}

workflow REPORTING {
    take:
    ch_events
    samplesheet
    settings

    main:
    ch_inputs = ch_events.toList().map { entries ->
        entries = entries.sort { a, b ->
            groovy.json.JsonOutput.toJson(a[0]) <=> groovy.json.JsonOutput.toJson(b[0]) ?:
                a[1].collect { it.toString() }.join('\n') <=> b[1].collect { it.toString() }.join('\n')
        }
        def files = []
        def records = entries.collect { descriptor, sources ->
            if (!(descriptor instanceof Map)) error 'Invalid untyped report event'
            def indices = sources.collect { source ->
                files.add(source)
                files.size() - 1
            }
            descriptor + [file_indices: indices]
        }
        tuple(records, files)
    }
    REPORT(ch_inputs, samplesheet, file("${moduleDir}/../../assets/plasmid_report.Rmd"),
           file("${moduleDir}/../../bin/generate_report.R"), settings)

    emit:
    data_json = REPORT.out.data_json
    inputs_json = REPORT.out.inputs_json
    report_md = REPORT.out.report_md
    report_html = REPORT.out.report_html
    methods_md = REPORT.out.methods_md
}
