include { semibinRuntime; semibinRequireRuntime; semibinRuntimeBase64 } from '../../../../lib/semibin_runtime'

process SEMIBIN_SINGLEEASYBIN {
    cache 'deep'
    tag "${meta.id}"
    label 'process_medium'
    label 'process_gpu'

    conda "${task.accelerator ? "${moduleDir}/environment.gpu.yml" : "${moduleDir}/environment.yml"}"
    container "${workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container
        ? (task.accelerator
            ? 'https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/fb/fbd557d49df87acd78159a1be8a78dc8fec2030a0ab3e26b11b16ed112ad5e57/data'
            : 'https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/4c/4c049230e87478349b2ecca53156faedfb077df85a4f6deaa8d0b22bd8a975c4/data')
        : (task.accelerator
            ? 'community.wave.seqera.io/library/semibin_pytorch-gpu_cuda-version:d7e398c7556966b1'
            : 'community.wave.seqera.io/library/semibin:2.4.1--594344a862aee1b8')}"

    input:
    tuple val(meta), path(fasta), path(bam), val(runtime_identity), path(runtime_receipt)
    // Explicit regular files: helper changes participate in deep caching.
    path(autoplasm_helper_0, stageAs: 'semibin_output_state.py')
    path(resource_helper, stageAs: 'semibin_runtime_resources.py')

    output:
    tuple val(meta), path("${prefix}/*.csv"), emit: csv
    tuple val(meta), path("${prefix}/*.pt"), emit: model, optional: true
    tuple val(meta), path("${prefix}/*.tsv"), emit: tsv
    tuple val(meta), path("${prefix}/output_bins/*.fa.gz"), emit: output_fasta, optional: true
    tuple val(meta), path("${prefix}/binning_status.json"), emit: state
    tuple val("${task.process}"), val('SemiBin'), eval("SemiBin2 --version"), emit: versions_semibin, topic: versions
    tuple val("${task.process}"), val('cuda'), eval('python -c "import torch; print(torch.version.cuda or \'no CUDA available\')"'), emit: versions_cuda, topic: versions
    tuple val("${task.process}"), val(meta), path("${meta.id}.SEMIBIN_SINGLEEASYBIN.task_command.sh"),
          val('SemiBin2 --version'), eval('SemiBin2 --version'),
          eval("sha256sum '${meta.id}.SEMIBIN_SINGLEEASYBIN.task_command.sh'"), emit: task_provenance


    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def args2 = task.ext.args2 ?: ""
    prefix = task.ext.prefix ?: "${meta.id}"
    def engine = task.accelerator ? 'gpu' : 'cpu'
    def runtime = semibinRuntime(task, workflow.containerEngine, meta)
    semibinRequireRuntime(runtime_identity, runtime)
    def runtime64 = semibinRuntimeBase64(runtime)
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.SEMIBIN_SINGLEEASYBIN.task_command.sh'

    python semibin_runtime_resources.py --runtime-base64 '${runtime64}' --verify ${runtime_receipt} --execute -- ${args} single_easy_bin --input-fasta ${fasta} --input-bam ${bam} --output ${prefix} -t ${task.cpus} --engine ${engine} ${args2}

    python3 semibin_output_state.py --output "${prefix}"
    """

    stub:
    semibinRequireRuntime(runtime_identity, semibinRuntime(task, workflow.containerEngine, meta))
    prefix = task.ext.prefix ?: "${meta.id}"
    """
    cp -- "\${BASH_SOURCE[0]}" '${meta.id}.SEMIBIN_SINGLEEASYBIN.task_command.sh'
    mkdir ${prefix}
    touch ${prefix}/{contig_bins,recluster_bins_info}.tsv
    touch ${prefix}/{data,data_split}.csv
    mkdir ${prefix}/output_bins
    echo '{"schema":1,"state":"stub_not_validated","bin_count":null,"bins":[]}' > ${prefix}/binning_status.json
    """
}


/* Always refresh installed resources before the scientific task cache lookup.
 * Divergent per-name runtime/argument overrides are rejected by the consumer
 * script closure before lookup. Configure both names with a shared selector.
 */
process SEMIBIN_RESOURCE_PROBE {
    cache false
    tag "${meta.id}"
    label 'process_medium'
    label 'process_gpu'

    conda "${task.accelerator ? "${moduleDir}/environment.gpu.yml" : "${moduleDir}/environment.yml"}"
    container "${workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container
        ? (task.accelerator
            ? 'https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/fb/fbd557d49df87acd78159a1be8a78dc8fec2030a0ab3e26b11b16ed112ad5e57/data'
            : 'https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/4c/4c049230e87478349b2ecca53156faedfb077df85a4f6deaa8d0b22bd8a975c4/data')
        : (task.accelerator
            ? 'community.wave.seqera.io/library/semibin_pytorch-gpu_cuda-version:d7e398c7556966b1'
            : 'community.wave.seqera.io/library/semibin:2.4.1--594344a862aee1b8')}"

    input:
    tuple val(meta), path(fasta), path(bam)
    path(resource_helper, stageAs: 'semibin_runtime_resources.py')

    output:
    tuple val(meta), path('semibin_runtime_identity.json'), emit: identity

    script:
    def args = task.ext.args ?: ''
    def args2 = task.ext.args2 ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    def engine = task.accelerator ? 'gpu' : 'cpu'
    def runtime64 = semibinRuntimeBase64(semibinRuntime(task, workflow.containerEngine, meta))
    """
    python semibin_runtime_resources.py --runtime-base64 '${runtime64}' --output semibin_runtime_identity.json -- ${args} single_easy_bin --input-fasta ${fasta} --input-bam ${bam} --output ${prefix} -t ${task.cpus} --engine ${engine} ${args2}
    """

    stub:
    def identity = [schema_version: 1, stub: true, runtime: semibinRuntime(task, workflow.containerEngine, meta)]
    def encoded = semibinRuntimeBase64(identity)
    """
    printf '%s' '${encoded}' | base64 -d > semibin_runtime_identity.json
    """
}
