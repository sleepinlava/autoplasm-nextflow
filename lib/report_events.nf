/* Reporting records describe outputs from this execution, never publishDir.
 * Only detection files needed for counts are staged; other outputs are
 * completion/version evidence, without copying large BAMs or databases.
 */
def reportValue(value) {
    if (value instanceof Map) return value.collectEntries { k, v -> [(k.toString()): reportValue(v)] }
    if (value instanceof Collection) return value.collect { reportValue(it) }
    if (value == null || value instanceof Number || value instanceof Boolean) return value
    return value.toString()
}

def reportEvidence(recordedOutputs, section, producer) {
    def outputs = recordedOutputs.channels
    def streams = outputs.getNames().collect { outputName ->
        if (outputName == 'commands') {
            return outputs.getProperty(outputName).map { command ->
                tuple([section:section,producer:producer,kind:'evidence',output:'execution_script',
                       evidence:command.toString()], [command])
            }
        }
        if (outputName == 'cohort_provenance') {
            return outputs.getProperty(outputName).map { process, command, probe, stdout, checksum, cohort_csv ->
                def members = cohort_csv.toString().trim() ? cohort_csv.toString().trim().split(',') as List : []
                tuple([section: section, producer: producer, kind: 'runtime_command', cohort: true,
                       task_process: process.toString(),
                       sample_id: 'cohort:' + process.toString(),
                       analysis_sample_id: 'cohort:' + process.toString(),
                       cohort_samples: members,
                       script_sha256: checksum.toString().tokenize()[0],
                       runtime_probe: [command: probe.toString(), stdout: stdout.toString()]], [command])
            }
        }
        if (outputName == 'task_provenance') {
            return outputs.getProperty(outputName).map { process, meta, command, probe, stdout, checksum ->
                def is_cohort = meta.cohort == true
                def original = meta.gplas_original_meta ?: meta
                def record = [section: section, producer: producer, kind: 'runtime_command',
                              task_process: process.toString(),
                              script_sha256: checksum.toString().tokenize()[0],
                              runtime_probe: [command: probe.toString(), stdout: stdout.toString()]]
                if (is_cohort) {
                    def members = meta.cohort_samples
                    record['sample_id'] = 'cohort:' + process.toString()
                    record['analysis_sample_id'] = 'cohort:' + process.toString()
                    record['cohort'] = true
                    record['cohort_samples'] = members instanceof Collection ? members.collect { it.toString() } : []
                } else {
                    record['sample_id'] = original.id.toString()
                    record['analysis_sample_id'] = meta.id.toString()
                }
                tuple(record, [command])
            }
        }
        outputs.getProperty(outputName).map { value ->
            tuple([section: section, producer: producer, kind: 'evidence', output: outputName,
                   evidence: reportValue(value)], [])
        }
    }
    return streams.inject(Channel.empty()) { merged, stream -> merged.mix(stream) }
}

def reportSamples(channel, kind, producer) {
    return channel.map { meta, source ->
        tuple([section: '04_plasmid_detection', producer: producer, kind: kind,
               sample_id: meta.id.toString()], [source])
    }
}

def reportSettings(params) {
    def keys = ['platform', 'project_name', 'short_read_assembler', 'hybrid_assembler',
                'consensus_method', 'consensus_weights', 'plasmid_detection_tools',
                'plasmid_binning_tools', 'typing_tools', 'typing_optional_tools',
                'annotation_tools', 'annotation_optional_tools', 'host_prediction_tools',
                'mag_tools', 'comparative_tools', 'comparative_optional_tools',
                'host_plasmid_linking', 'host_linking_methods', 'host_linking_optional_methods',
                'run_fastqc', 'run_multiqc', 'run_diversity', 'run_differential_internal',
                'run_differential_deseq2', 'run_network', 'short_read_protocol', 'catalogue_identity', 'catalogue_coverage',
                'protocol_complete_ids', 'protocol_host_models', 'mostplas_source','mostplas_threshold','plsdb_fasta','plsdb_hosts',
                'protocol_host_strata','protocol_host_subject','protocol_host_bootstraps','protocol_mag_min_completeness','protocol_mag_max_contamination',
                'protocol_arg_window','protocol_evolution','protocol_tree_min_members','protocol_tree_min_core','protocol_strain',
                'protocol_strain_min_coverage','protocol_strain_ani','protocol_strain_min_compared_bases','protocol_min_breadth',
                'beta_normalization','ecology_formula','ecology_block','ecology_permutations','run_ancombc2','ancombc2_formula','ancombc2_random_formula','ancombc2_prevalence']
    return keys.findAll { params.containsKey(it) }.collectEntries { key -> [(key): reportValue(params[key])] }
}
