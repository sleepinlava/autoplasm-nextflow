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
        if (outputName == 'task_provenance') {
            return outputs.getProperty(outputName).map { process, meta, command, probe, stdout, checksum ->
                def original = meta.gplas_original_meta ?: meta
                tuple([section: section, producer: producer, kind: 'runtime_command',
                       task_process: process.toString(), sample_id: original.id.toString(),
                       analysis_sample_id: meta.id.toString(),
                       script_sha256: checksum.toString().tokenize()[0],
                       runtime_probe: [command: probe.toString(), stdout: stdout.toString()]], [command])
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
                'run_differential_deseq2', 'run_network']
    return keys.findAll { params.containsKey(it) }.collectEntries { key -> [(key): reportValue(params[key])] }
}
